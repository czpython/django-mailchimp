import json
import hashlib
import six
try:
    from urllib import quote_plus, urlencode
except ImportError:
    from urllib.parse import quote_plus, urlencode
try:
    from urllib2 import build_opener
except ImportError:
    from urllib.request import build_opener
from warnings import warn

from requests import request
from requests.exceptions import HTTPError

from .utils import ceil_dt, transform_datetime


def remove_empty(d):
    """
    Helper function that removes all keys from a dictionary (d),
    that have an empty value.
    """
    for key in d.keys():
        if not d[key]:
            del d[key]
    return d


class ChimpyException(Exception):
    pass


class ChimpyWarning(Warning):
    pass


class Connection(object):
    """mailchimp api connection"""

    output = "json"
    version = '3.0'

    def __init__(self, apikey=None, secure=False):
        self._apikey = apikey

        proto = 'https' if secure else 'http'

        if '-' in apikey:
            dc = apikey.split('-')[1]
        else:
            dc = 'us1'

        self.root = '{}://{}.api.mailchimp.com/{}/'.format(proto, dc, self.version)

    def _get_email_hash(self, email):
        md = hashlib.md5()
        md.update(email.lower())
        return md.hexdigest()

    def make_request(self, method="GET", path=None, **kwargs):
        if path:
            url = '{}{}'.format(self.root, path)
        else:
            url = self.root

        queries = kwargs.get('queries')

        if queries:
            queries = remove_empty(queries)

        payload = kwargs.get('body') or {}

        if payload:
            payload = remove_empty(payload)
            payload = json.dumps(payload)

        response = request(
            method,
            url=url,
            params=queries,
            data=payload,
            headers={'content-type': 'application/json'},
            auth=('chimp', self._apikey),
        )

        if response.status_code == 204:
            return {'success': True}

        try:
            response.raise_for_status()
        except HTTPError as e:
            message = response.json()['detail']
            raise ChimpyException(message)
        return response.json()

    def ping(self):
        data = self.make_request(queries={'fields': 'account_name'})
        return 'account_name' in data

    def lists(self, limit=25):
        all_lists = []
        start = 0
        has_more = True

        while has_more:
            queries = {'count': limit, 'offset': start}
            data = self.make_request(path='lists', queries=queries)
            all_lists.extend(data['lists'])
            has_more = int(data['total_items']) > len(all_lists)
            start += 1
        return all_lists

    def list_batch_update(self, id, batch, update_existing=False):
        path = 'lists/{}'.format(id)
        payload = {
            'members': batch,
            'update_existing': update_existing,
        }
        return self.make_request('POST', path, body=payload)

    def list_subscribe(self,
                       id,
                       email_address,
                       merge_vars,
                       email_type='text',
                       status='subscribed',
                       interests=None):
        path = 'lists/{}/members'.format(id)
        payload = {
            'email_type': email_type,
            'status': status,
            'merge_fields': merge_vars,
            'email_address': email_address,
            'interests': interests,
        }
        return self.make_request('POST', path, body=payload)

    def list_unsubscribe(self,
                         id,
                         email_address,
                         delete_member=False):
        email_hash = self._get_email_hash(email_address)
        path = 'lists/{}/members/{}'.format(id, email_hash)

        if delete_member:
            return self.make_request('DELETE', path)

        payload = {'status': 'unsubscribed'}
        return self.make_request('PATCH', path, body=payload)

    def list_update_member(self,
                           id,
                           email_address,
                           merge_vars,
                           email_type=None,
                           interests=None):
        email_hash = self._get_email_hash(email_address)
        path = 'lists/{}/members/{}'.format(id, email_hash)
        payload = {
            'email_type': email_type,
            'merge_fields': merge_vars,
            'email_address': email_address,
            'interests': interests,
        }
        return self.make_request('PATCH', path, body=payload)

    def list_member_info(self, id, email_address):
        email_hash = self._get_email_hash(email_address)
        path = 'lists/{}/members/{}'.format(id, email_hash)
        return self.make_request('GET', path)

    def list_member_info_from_id(self, id, email_id):
        path = 'lists/{}/members'.format(id)
        queries = {'unique_email_id': email_id}
        return self.make_request('GET', path, queries=queries)

    def list_members(self, id, status='subscribed', since=None, offset=0, limit=100):
        path = 'lists/{}/members'.format(id)
        queries = {
            'status': status,
            'since_last_changed': since,
            'offset': offset,
            'count': limit,
        }
        return self.make_request('GET', path, queries=queries)

    def list_interest_groupings_add(self, id, title, type):
        path = 'lists/{}/interest-categories'.format(id)
        payload = {'title': title, 'type': type}
        return self.make_request('POST', path, body=payload)

    def list_interest_groupings_del(self, id, grouping_id):
        """
        Delete an existing Interest Grouping - this will permanently delete all
        contained interest groups and will remove those selections from all list
        members
        """
        path = 'lists/{}/interest-categories/{}'.format(id, grouping_id)
        return self.make_request('DELETE', path)

    def list_interest_groupings(self, id):
        path = 'lists/{}/interest-categories'.format(id)
        return self.make_request('GET', path)

    def list_interest_groups(self, id, grouping_id, count=30):
        path = 'lists/{}/interest-categories/{}/interests'.format(id, grouping_id)
        return self.make_request('GET', path, queries={'count': count})

    def list_interest_group_add(self, id, grouping_id, name):
        path = 'lists/{}/interest-categories/{}/interests'.format(id, grouping_id)
        payload = {'name': name}
        return self.make_request('POST', path, body=payload)

    def list_interest_group_del(self, id, grouping_id, group_id):
        path = 'lists/{}/interest-categories/{}/interests/{}'.format(id, grouping_id, group_id)
        return self.make_request('DELETE', path)

    def list_interest_group_update(self, id, grouping_id, group_id, new_name):
        path = 'lists/{}/interest-categories/{}/interests/{}'.format(id, grouping_id, group_id)
        payload = {'name': new_name}
        return self.make_request('PATCH', path, body=payload)

    def list_merge_vars(self, id):
        path = 'lists/{}/merge-fields'.format(id)
        return self.make_request('GET', path)

    def list_merge_var_add(self, id, tag, name, req=False, type='text'):
        path = 'lists/{}/merge-fields'.format(id)
        payload = {
            'tag': tag.upper(),
            'name': name,
            'req': req,
            'type': type,
        }
        return self.make_request('POST', path, body=payload)

    def list_merge_var_del(self, id, tag_id):
        path = 'lists/{}/merge-fields/{}'.format(id, tag_id)
        return self.make_request('DELETE', path)

    def list_webhooks(self, id):
        path = 'lists/{}/webhooks'.format(id)
        return self.make_request('GET', path)

    def list_webhook_add(self, id, url, actions, sources):
        path = 'lists/{}/webhooks'.format(id)
        payload = {
            'url': url,
            'events': actions,
            'sources': sources,
        }
        return self.make_request('POST', path, body=payload)

    def list_webhook_del(self, id, webhook_id):
        path = 'lists/{}/webhooks/{}'.format(id, webhook_id)
        return self.make_request('DELETE', path)

    def campaigns(self, list_id=None, folder_id=None,
                  sent_since=None, sent_before=None,
                  start=0, limit=50):
        """Get the list of campaigns and their details matching the specified filters.
        Timestamps should be passed as datetime objects.
        """
        queries = {
            'count': limit,
            'offset': start,
            'since_send_time': transform_datetime(sent_since),
            'before_send_time': transform_datetime(sent_before),
            'list_id': list_id,
            'folder_id': folder_id,
        }
        return self.make_request('GET', 'campaigns', queries=queries)

    def campaign(self, cid):
        path = 'campaigns/{}'.format(cid)
        return self.make_request('GET', path)

    def campaign_create(self, campaign_type, settings, **kwargs):
        # enforce the 100 char limit (urlencoded!!!)
        title = settings.get('title', settings['subject_line'])
        if isinstance(title, six.text_types):
            title = title.encode('utf-8')
        titlelen = len(quote_plus(title))

        if titlelen > 99:
            title = title[:-(titlelen - 96)] + '...'
            warn("cropped campaign title to fit the 100 character limit, new title: '%s'" % title, ChimpyWarning)
        subject = settings['subject_line']
        if isinstance(subject, six.text_types):
            subject = subject.encode('utf-8')
        subjlen = len(quote_plus(subject))

        if subjlen > 99:
            subject = subject[:-(subjlen - 96)] + '...'
            warn("cropped campaign subject to fit the 100 character limit, new subject: '%s'" % subject, ChimpyWarning)

        settings.update({
            'title': title,
            'subject_line': subject,
        })

        payload = {
            'settings': settings,
            'type': campaign_type,
        }
        payload.update(kwargs)
        return self.make_request('POST', 'campaigns', body=payload)

    def campaign_set_content(self, cid, template):
        path = 'campaigns/{}/content'.format(cid)
        payload = {
            'template': {'id': template.id, 'sections': template.as_dict()}
        }
        return self.make_request('PUT', path, body=payload)

    def campaign_content(self, cid):
        """Get the content (both html and text) for a campaign
        """
        path = 'campaigns/{}/content'.format(cid)
        return self.make_request('GET', path)

    def campaign_delete(self, cid):
        path = 'campaigns/{}'.format(cid)
        return self.make_request('DELETE', path)

    def campaign_pause(self, cid):
        path = 'campaigns/{}/actions/pause'.format(cid)
        return self.make_request('POST', path)

    def campaign_replicate(self, cid):
        path = 'campaigns/{}/actions/replicate'.format(cid)
        return self.make_request('POST', path)

    def campaign_resume(self, cid):
        path = 'campaigns/{}/actions/resume'.format(cid)
        return self.make_request('POST', path)

    def campaign_schedule(self, cid, schedule_time):
        path = 'campaigns/{}/actions/schedule'.format(cid)
        schedule_time = ceil_dt(schedule_time)
        schedule_time = transform_datetime(schedule_time)
        payload = {
            'schedule_time': schedule_time,
        }
        return self.make_request('POST', path, body=payload)

    def campaign_unschedule(self, cid):
        path = 'campaigns/{}/actions/unschedule'.format(cid)
        return self.make_request('POST', path)

    def campaign_send_now(self, cid):
        path = 'campaigns/{}/actions/send'.format(cid)
        return self.make_request('POST', path)

    def campaign_send_test(self, cid, test_emails, send_type='html'):
        path = 'campaigns/{}/actions/test'.format(cid)

        if isinstance(test_emails, six.string_types):
            test_emails = [test_emails]

        payload = {
            'test_emails': test_emails,
            'send_type': send_type,
        }
        return self.make_request('POST', path, body=payload)

    def templates(self, template_type='user', start=0, limit=50):
        """
        Retrieve various templates available in the system, allowing something
        similar to our template gallery to be created.
        """
        queries = {
            'count': limit,
            'offset': start,
            "type" : template_type,
        }
        return self.make_request('GET', 'templates', queries=queries)

    def template_info(self, template_id):
        """
        Pull details for a specific template to help support editing
        """
        path = 'templates/{}'.format(template_id)
        return self.make_request('GET', path)

    def campaign_templates(self, limit=50):
        templates = []
        start = 0
        has_more = True

        while has_more:
            data = self.templates(template_type='user', start=start, limit=limit)
            templates.extend(data['templates'])
            has_more = int(data['total_items']) > len(templates)
            start += 1
        return templates

    def campaign_update(self, cid, name, value):
        """Update just about any setting for a campaign that has not been sent.
        http://apidocs.mailchimp.com/api/1.3/campaignupdate.func.php
        """

        return self._api_call(method='campaignUpdate', cid=cid, name=name, value=value)

    def folder_add(self, name, folder_type='campaign'):
        """
        Add a new folder to file campaigns or autoresponders in
        http://apidocs.mailchimp.com/api/1.3/folderadd.func.php
        """
        return self._api_call('folderAdd', name=name, type=folder_type)

    def folder_del(self, folder_id, folder_type='campaign'):
        """
        Delete a campaign or autoresponder folder.
        http://apidocs.mailchimp.com/api/1.3/folderdel.func.php
        """
        return self._api_call('folderDel', fid=folder_id, type=folder_type)

    def folder_update(self, folder_id, name, folder_type='campaign'):
        """
        Update the name of a folder for campaigns or autoresponders
        http://apidocs.mailchimp.com/api/1.3/folderupdate.func.php
        """
        return self._api_call('folderUpdate', fid=folder_id, name=name, type=folder_type)

    def folders(self):
        """List all the folders for a user account.
        http://apidocs.mailchimp.com/api/1.3/folders.func.php
        """

        return self._api_call(method='folders')
