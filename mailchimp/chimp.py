from __future__ import unicode_literals

import datetime

from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site

from .chimpy.chimpy import Connection as BaseConnection, ChimpyException
from .utils import wrap, build_dict, Cache, WarningLogger
from .exceptions import (
    MCCampaignDoesNotExist,
    MCListDoesNotExist,
    MCConnectionFailed,
    MCTemplateDoesNotExist,
    MCFolderDoesNotExist,
)
from .constants import *
from .settings import WEBHOOK_KEY


class SegmentCondition(object):
    OPERATORS = {
        'is': lambda a,b: a == b,
        'not': lambda a,b: a != b,
        'gt': lambda a,b: a > b,
        'lt': lambda a,b: a < b,
        'like': lambda a,b: a in b,
        'nlike': lambda a,b: a not in b,
        'starts': lambda a,b: str(a).startswith(str(b)),
        'ends': lambda a,b: str(a).endswith(str(b))
    }

    def __init__(self, condition_type, field, op, value):
        self.condition_type = condition_type
        self.field = field
        self.op = op
        self.value = value
        check_function_name = 'check_%s' % self.field
        if not hasattr(self, check_function_name):
            check_function_name = 'merge_check'
        self.checker = getattr(self, check_function_name)

    def check(self, member):
        return self.checker(member)

    def check_interests(self, member):
        interests = self.value.split(',')
        if self.op == 'all':
            for interest in interests:
                if interest not in member.interests:
                    return False
            return True
        elif self.op == 'one':
            for interest in interests:
                if interest in member.interests:
                    return True
            return False
        else:
            for interest in interests:
                if interest in member.interests:
                    return False
            return True

    def merge_check(self, member):
        return self.OPERATORS[self.op](member.merges[self.field.upper()], self.value)


class BaseChimpObject(object):
    _attrs = ()
    _methods = ()

    verbose_attr = 'id'
    cache_key = 'id'

    def __init__(self, master, info):
        self.master = master

        for attr in self._attrs:
            lookup = lambda d, key: d[key]
            keys = attr.split('.')
            value = reduce(lookup, keys, info)
            setattr(self, keys[-1], value)

        base = self.__class__.__name__.lower()
        self.cache = master.cache.get_child_cache(getattr(self, self.cache_key))
        self.con = master.con

        for method in self._methods:
            setattr(self, method, wrap(base, self.master.con, method, self.id))

    def __repr__(self):
        verbose = getattr(self, self.verbose_attr).encode('utf-8')
        return '<%s object: %s>' % (self.__class__.__name__, verbose)

    def __str__(self):
        return unicode(self).encode('utf-8')


class Campaign(BaseChimpObject):
    _attrs = ('archive_url', 'create_time', 'emails_sent', 'settings.folder_id',
              'settings.from_name', 'id', 'settings.inline_css', 'recipients.list_id',
              'send_time', 'status', 'settings.subject_line', 'settings.title',
              'settings.to_name', 'type')

    _methods =  ('delete', 'pause', 'replicate', 'resume', 'schedule',
                 'send_now', 'send_test', 'unschedule')

    verbose_attr = 'subject_line'

    def __init__(self, master, info):
        super(Campaign, self).__init__(master, info)
        try:
            self.list = self.master.get_list_by_id(self.list_id)
        except MCListDoesNotExist:
            self.list = None
        self._content = None
        self.frozen_info = info

    def __unicode__(self):
        return self.subject

    @property
    def content(self):
        return self.get_content()

    def get_content(self):
        if self._content is None:
            self._content = self.con.campaign_content(self.id)
        return self._content

    def send_now_async(self):
        return self.send_now()

    def delete(self):
        return self.con.campaign_delete(self.id)

    def pause(self):
        return self.con.campaign_pause(self.id)

    def update(self):
        status = []
        for key, value in self._get_diff():
            status.append(self.con.campaign_update(self.id, key, value))
        return all(status)

    def _get_diff(self):
        diff = []
        new_frozen = {}
        for key in self._attrs:
            current = getattr(self, key)
            if self.frozen_info[key] != current:
                diff.append((key, current))
            new_frozen[key] = current
        self.frozen_info = new_frozen
        return diff

    @property
    def is_sent(self):
        return self.status == 'sent'


class Member(BaseChimpObject):
    _attrs = ('email', 'timestamp')

    _extended_attrs = ('id', 'ip_opt', 'ip_signup', 'merge_fields', 'status', 'interests')

    verbose_attr = 'email'
    cache_key = 'email'

    def __init__(self, master, info):
        super(Member, self).__init__(master, info)

    def __unicode__(self):
        return self.email

    def __getattr__(self, attr):
        if attr in self._extended_attrs:
            return self.info[attr]
        raise AttributeError(attr)

    @property
    def merges(self):
        return self.merge_fields

    @property
    def info(self):
        return self.get_info()

    def get_info(self):
        return self.cache.get('list_member_info', self.con.list_member_info, self.master.id, self.email)

    def update(self):
        return self.con.list_update_member(self.master.id, self.email, self.merges, interests=self.interests)


class LazyMemberDict(dict):
    def __init__(self, master):
        super(LazyMemberDict, self).__init__()
        self._list = master

    def __getitem__(self, key):
        if key in self:
            return super(LazyMemberDict, self).__getitem__(key)
        value = self._list.get_member(key)
        self[key] = value
        return value


class List(BaseChimpObject):
    '''
    This represents a mailing list. Most of the methods (defined in _methods) are wrappers of the flat
    API found in chimpy.chimpy. As such, signatures are the same.
    '''
    _methods = ('batch_subscribe',
                'batch_unsubscribe',
                'subscribe',
                'unsubscribe')

    _attrs = ('id', 'date_created', 'name', 'stats')

    verbose_attr = 'name'

    def __init__(self, *args, **kwargs):
        super(List, self).__init__(*args, **kwargs)
        self.members = LazyMemberDict(self)

    def segment_test(self, match, conditions):
        return self.master.con.campaign_segment_test(self.id, {'match': match, 'conditions': conditions})

    def list_interest_groupings(self):
        return self.master.con.list_interest_groupings(self.id)

    def add_interest_group(self, groupname, grouping_id=None):
        grouping_id = grouping_id or self._default_grouping()
        return self.master.con.list_interest_group_add(self.id, groupname, grouping_id)

    def remove_interest_group(self, groupname, grouping_id=None):
        grouping_id = grouping_id or self._default_grouping()
        return self.master.con.list_interest_group_del(self.id, groupname, grouping_id)

    def update_interest_group(self, oldname, newname, grouping_id=None):
        grouping_id = grouping_id or self._default_grouping()
        return self.master.con.list_interest_group_update(self.id, oldname, newname, grouping_id)

    def add_interests_if_not_exist(self, *interests):
        self.cache.flush('interest_groups')
        interest_groups = self.interest_groups['groups']
        names = set(g['name'] for g in interest_groups)
        for interest in set(interests):
            if interest not in names:
                self.add_interest_group(interest)
                interest_groups.append(interest)

    def _default_grouping(self):
        if not hasattr(self, '_default_grouping_id'):
            groupings = self.list_interest_groupings()
            if len(groupings):
                self._default_grouping_id = groupings[0]['id']
            else:
                self._default_grouping_id = None
        return self._default_grouping_id

    @property
    def webhooks(self):
        return self.get_webhooks()

    def get_webhooks(self):
        return self.cache.get('webhooks', self.master.con.list_webhooks, self.id)

    def add_webhook(self, url, actions, sources):
        return self.master.con.list_webhook_add(self.id, url, actions, sources)

    def remove_webhook(self, url):
        return self.master.con.list_webhook_del(self.id, url)

    def add_webhook_if_not_exists(self, url, actions, sources):
        for webhook in self.webhooks:
            if webhook['url'] == url:
                return True
        return self.add_webhook(url, actions, sources)

    def install_webhook(self):
        domain = Site.objects.get_current().domain
        if not (domain.startswith('http://') or domain.startswith('https://')):
            domain = 'http://%s' % domain
        if domain.endswith('/'):
            domain = domain[:-1]
        url = domain + reverse('mailchimp_webhook', kwargs={'key': WEBHOOK_KEY})
        actions = {'subscribe': True,
                   'unsubscribe': True,
                   'profile': True,
                   'cleaned': True,
                   'upemail': True,}
        sources = {'user': True,
                   'admin': True,
                   'api': False}
        return self.add_webhook_if_not_exists(url, actions, sources)

    def add_merge(self, key, desc, req=None):
        req = req or {}
        return self.master.con.list_merge_var_add(self.id, key, desc, req if req else False)

    def remove_merge(self, key):
        return self.master.con.list_merge_var_del(self.id, key)

    def add_merges_if_not_exists(self, *new_merges):
        self.cache.flush('merges')
        merges = [m['tag'].upper() for m in self.merges]
        for merge in set(new_merges):
            if merge.upper() not in merges:
                self.add_merge(merge, merge, False)
                merges.append(merge.upper())

    @property
    def merges(self):
        return self.get_merges()

    def get_merges(self):
        return self.cache.get('merges', self.master.con.list_merge_vars, self.id)

    def __unicode__(self):
        return self.name

    def get_member(self, email):
        try:
            data = self.master.con.list_member_info(self.id, email)
        except ChimpyException:
            return None
        # actually it would make more sense giving the member everything
        memberdata = {}
        memberdata['timestamp'] = data['timestamp_signup']
        memberdata['email'] = data['email_address']
        return Member(self, memberdata)

    def filter_members(self, segment_opts):
        """
        segment_opts = {'match': 'all' if self.segment_options_all else 'any',
        'conditions': json.loads(self.segment_options_conditions)}
        """
        mode = all if segment_opts['match'] == 'all' else any
        conditions = [SegmentCondition(**dict((str(k), v) for k,v in c.items())) for c in segment_opts['conditions']]
        for email, member in self.members.items():
            if mode([condition.check(member) for condition in conditions]):
                yield member


class BoundTemplate(object):

    def __init__(self, template, data):
        self.template = template
        self.data = data
        self.id = self.template.id

    def __iter__(self):
        return iter(self.data.items())

    def as_dict(self):
        return dict(self)


class Template(BaseChimpObject):
    _attrs = ('id', 'name', 'thumbnail', 'type')

    verbose_attr = 'name'

    def build(self, **kwargs):
        return BoundTemplate(self, kwargs)


class Folder(BaseChimpObject):
    _attrs = ('id', 'name', 'type', 'date_created')

    def __init__(self, master, info):
        info['id'] = info['folder_id']
        del info['folder_id']

        super(Folder, self).__init__(master, info)


class Connection(object):
    REGULAR = REGULAR_CAMPAIGN
    PLAINTEXT = PLAINTEXT_CAMPAIGN
    ABSPLIT = ABSPLIT_CAMPAIGN
    RSS = RSS_CAMPAIGN
    TRANS = TRANS_CAMPAIGN
    AUTO = AUTO_CAMPAIGN
    DOES_NOT_EXIST = {
        'templates': MCTemplateDoesNotExist,
        'campaigns': MCCampaignDoesNotExist,
        'lists': MCListDoesNotExist,
        'folders': MCFolderDoesNotExist,
    }

    def __init__(self, api_key=None, secure=False, check=True):
        self._secure = secure
        self._check = check
        self._api_key = None
        self.con = None
        self.is_connected = False
        if api_key is not None:
            self.connect(api_key)

    def connect(self, api_key):
        self._api_key = api_key
        self.cache = Cache(api_key)
        self.warnings = WarningLogger()
        self.con = self.warnings.proxy(BaseConnection(self._api_key, self._secure))
        if self._check and not self.ping():
            raise MCConnectionFailed()
        self.is_connected = True

    def ping(self):
        return self.con.ping()

    @property
    def campaigns(self):
        return self.get_campaigns()

    def get_campaigns(self):
        return self.cache.get('campaigns', self._get_campaigns)

    @property
    def lists(self):
        return self.get_lists()

    def get_lists(self):
        return self.cache.get('lists', self._get_lists)

    @property
    def templates(self):
        return self.get_templates()

    def get_templates(self):
        return self.cache.get('templates', self._get_templates)

    def _get_campaigns(self):
        return build_dict(self, Campaign, self.con.campaigns())

    def _get_lists(self):
        return build_dict(self, List, self.con.lists())

    def _get_templates(self):
        templates = self.con.campaign_templates()
        return build_dict(self, Template, templates)

    @property
    def folders(self):
        return self.get_folders()

    def get_folders(self):
        return self.cache.get('folders', self._get_folders)

    def _get_folders(self):
        return build_dict(self, Folder, self.con.folders(), key='folder_id')

    def get_list_by_id(self, id):
        return self._get_by_id('lists', id)

    def get_campaign_by_id(self, id):
        return build_dict(self, Campaign, [self.con.campaign(id)])[id]

    def get_template_by_id(self, id):
        return self._get_by_id('templates', id)

    def get_template_by_name(self, name):
        return self._get_by_key('templates', 'name', name)

    def get_folder_by_id(self, id):
        return self._get_by_id('folders', id)

    def get_folder_by_name(self, name):
        return self._get_by_key('folders', 'name', name)

    def _get_by_id(self, thing, id):
        try:
            return getattr(self, thing)[id]
        except KeyError:
            self.cache.flush(thing)
            try:
                return getattr(self, thing)[id]
            except KeyError:
                raise self.DOES_NOT_EXIST[thing](id)

    def _get_by_key(self, thing, name, key):
        for id, obj in getattr(self, thing).items():
            if getattr(obj, name) == key:
                return obj
        raise self.DOES_NOT_EXIST[thing]('%s=%s' % (name, key))

    def create_campaign(self, campaign_type, campaign_list, template, subject,
            reply_to, from_name, to_name, folder_id=None,
            tracking=None, title='', authenticate=False,
            analytics=None, auto_footer=False,
            auto_tweet=False, segment_opts=None, rss_opts=None):
        """
        Creates a new campaign and returns it for the arguments given.
        """
        tracking = tracking or {'opens':True, 'html_clicks': True}

        if analytics:
            tracking.update(analytics)

        recipients = {
            'list_id': campaign_list.id,
        }
        segment_opts = segment_opts or {}

        if segment_opts.get('conditions', None):
            recipients['segment_opts'] = segment_opts

        settings = {}

        if title:
            settings['title'] = title
        else:
            settings['title'] = subject

        settings['reply_to'] = reply_to
        settings['subject_line'] = subject
        settings['from_name'] = from_name
        settings['to_name'] = to_name
        settings['authenticate'] = bool(authenticate)
        settings['auto_footer'] = bool(auto_footer)
        settings['auto_tweet'] = bool(auto_tweet)

        if title:
            settings['title'] = title
        else:
            settings['title'] = subject

        if folder_id:
            settings['folder_id'] = folder_id

        data = self.con.campaign_create(
            campaign_type,
            settings=settings,
            tracking=tracking,
            recipients=recipients,
            rss_opts=rss_opts,
        )

        self.con.campaign_set_content(
            cid=data['id'],
            template=template
        )

        camp = self.get_campaign_by_id(data['id'])
        camp.template_object = template
        return camp

    def queue(self, campaign_type, contents, list_id, template_id, subject,
        from_email, from_name, to_name, folder_id=None, tracking_opens=True,
        tracking_html_clicks=True, tracking_text_clicks=False, title=None,
        authenticate=False, google_analytics=None, auto_footer=False,
        auto_tweet=False, segment_options=False, segment_options_all=True,
        segment_options_conditions=None, type_opts=None, obj=None):
        from mailchimp.models import Queue
        segment_options_conditions = segment_options_conditions or []
        type_opts = type_opts or {}
        kwargs = locals().copy()
        del kwargs['Queue']
        del kwargs['self']
        return Queue.objects.queue(**kwargs)
