import urllib
import urllib2
import pprint
from utils import transform_datetime
from utils import flatten
from warnings import warn
import json
_debug = 1


class ChimpyException(Exception):
    pass

class ChimpyWarning(Warning):
    pass


class Connection(object):
    """mailchimp api connection"""

    output = "json"
    version = '1.3'

    def __init__(self, apikey=None, secure=False):
        self._apikey = apikey
        proto = 'http'
        if secure:
            proto = 'https'
        api_host = 'api.mailchimp.com'
        if '-' in apikey:
            key, dc = apikey.split('-')
        else:
            dc = 'us1'
        api_host = dc + '.' + api_host

        self.url = '%s://%s/%s/' % (proto, api_host, self.version)
        self.opener = urllib2.build_opener()
        self.opener.addheaders = [('Content-Type', 'application/x-www-form-urlencoded')]
        
    def _rpc(self, method, **params):
        """make an rpc call to the server"""

        params = urllib.urlencode(params, doseq=True)

        if _debug > 1:
            print __name__, "making request with parameters"
            pprint.pprint(params)
            print __name__, "encoded parameters:", params

        response = self.opener.open("%s?method=%s" %(self.url, method), params)
        data = response.read()
        response.close()

        if _debug > 1:
            print __name__, "rpc call received", data

        result = json.loads(data)

        try:
            if 'error' in result:
                raise ChimpyException("%s:\n%s" % (result['error'], params))
        except TypeError:
            # thrown when results is not iterable (eg bool)
            pass

        return result

    def _api_call(self, method, **params):
        """make an api call"""


        # flatten dict variables
        params = dict([(str(k), v.encode('utf-8') if isinstance(v, unicode) else v) for k,v in flatten(params).items()])
        params['output'] = self.output
        params['apikey'] = self._apikey

        return self._rpc(method=method, **params)

    def ping(self):
        return self._api_call(method='ping')

    def lists(self, limit=25):
        all_lists = []
        start = 0
        has_more = True
        while has_more:
            response = self._api_call(method='lists', start=start, limit=limit)
            all_lists += response['data']
            has_more = int(response['total']) > len(all_lists)
            start += 1
        return all_lists

    def list_batch_subscribe(self,
                             id,
                             batch,
                             double_optin=True,
                             update_existing=False,
                             replace_interests=False):

        return self._api_call(method='listBatchSubscribe',
                              id=id,
                              batch=batch,
                              double_optin=double_optin,
                              update_existing=update_existing,
                              replace_interests=replace_interests)

    def list_batch_unsubscribe(self,
                               id,
                               emails,
                               delete_member=False,
                               send_goodbye=True,
                               send_notify=False):

        return self._api_call(method='listBatchUnsubscribe',
                              id=id,
                              emails=emails,
                              delete_member=delete_member,
                              send_goodbye=send_goodbye,
                              send_notify=send_notify)

    def list_subscribe(self,
                       id,
                       email_address,
                       merge_vars,
                       email_type='text',
                       double_optin=True,
                       update_existing=False,
                       replace_interests=True,
                       send_welcome=False):
        return self._api_call(method='listSubscribe',
                              id=id,
                              email_address=email_address,
                              merge_vars=merge_vars,
                              email_type=email_type,
                              double_optin=double_optin,
                              update_existing=update_existing,
                              replace_interests=replace_interests,
                              send_welcome=send_welcome)

    def list_unsubscribe(self,
                         id,
                         email_address,
                         delete_member=False,
                         send_goodbye=True,
                         send_notify=True):
        return self._api_call(method='listUnsubscribe',
                              id=id,
                              email_address=email_address,
                              delete_member=delete_member,
                              send_goodbye=send_goodbye,
                              send_notify=send_notify)

    def list_update_member(self,
                           id,
                           email_address,
                           merge_vars,
                           email_type='',
                           replace_interests=True):
        return self._api_call(method='listUpdateMember',
                              id=id,
                              email_address=email_address,
                              merge_vars=merge_vars,
                              email_type=email_type,
                              replace_interests=replace_interests)

    def list_member_info(self, id, email_address):
        if isinstance(email_address, basestring):
            first = True
            email_address = [email_address]
        else:
            first = False
        result =  self._api_call(method='listMemberInfo',
                              id=id,
                              email_address=email_address)
        if first:
            return result['data'][0]
        return result

    def list_members(self, id, status='subscribed', since=None, start=0, limit=100):
        return self._api_call(method='listMembers', id=id, status=status, since=since, start=start, limit=limit)

    def list_interest_groupings_add(self, id, name, type, groups):
        """
        Add a new Interest Grouping - if interest groups for the List are not yet
        enabled, adding the first grouping will automatically turn them on.

        http://apidocs.mailchimp.com/api/1.3/listinterestgroupingadd.func.php
        """
        return self._api_call(method='listInterestGroupingAdd', id=id, name=name, type=type, groups=groups)

    def list_interest_groupings_del(self, grouping_id):
        """
        Delete an existing Interest Grouping - this will permanently delete all
        contained interest groups and will remove those selections from all list
        members

        http://apidocs.mailchimp.com/api/1.3/listinterestgroupingdel.func.php
        """
        return self._api_call(method='listInterestGroupingDel', grouping_id=grouping_id)

    def list_interest_groupings(self, id):
        return self._api_call(method='listInterestGroupings', id=id)

    def list_interest_groups(self, id, grouping_id, full=False):
        groupings = self.list_interest_groupings(id)
        grouping = None
        for g in groupings:
            if int(g['id']) == grouping_id:
                grouping = g
                break
        if not grouping:
            return []
        if not full:
            return [group['name'] for group in grouping['groups']]
        return grouping

    def list_interest_group_add(self, id, name, grouping_id):
        return self._api_call(method='listInterestGroupAdd', id=id, group_name=name, grouping_id=grouping_id)

    def list_interest_group_del(self, id, name, grouping_id):
        return self._api_call(method='listInterestGroupDel', id=id, group_name=name, grouping_id=grouping_id)

    def list_interest_group_update(self, id, old_name, new_name, grouping_id):
        return self._api_call(method='listInterestGroupUpdate', id=id, old_name=old_name, new_name=new_name, grouping_id=grouping_id)

    def list_merge_vars(self, id):
        return self._api_call(method='listMergeVars', id=id)

    def list_merge_var_add(self, id, tag, name, req=False):
        tag = tag.upper()
        return self._api_call(method='listMergeVarAdd', id=id, tag=tag, name=name, req=req)

    def list_merge_var_del(self, id, tag):
        return self._api_call(method='listMergeVarDel', id=id, tag=tag)
    
    def list_webhooks(self, id):
        return self._api_call(method='listWebhooks', id=id)
    
    # public static listWebhookAdd(string apikey, string id, string url, array actions, array sources)
    def list_webhook_add(self, id, url, actions, sources):
        return self._api_call(method='listWebhookAdd', id=id, url=url, actions=actions, sources=sources)
    
    def list_webhook_del(self, id, url):
        return self._api_call(method='listWebhookDel', id=id, url=url)

    def campaign_content(self, cid, archive_version=True):
        """Get the content (both html and text) for a campaign, exactly as it would appear in the campaign archive
        http://apidocs.mailchimp.com/api/1.3/campaigncontent.func.php
        """

        return self._api_call(method='campaignContent', cid=cid, for_archive=archive_version)

    def campaign_create(self, campaign_type, options, content, **kwargs):
        """Create a new draft campaign to send.
        http://www.mailchimp.com/api/1.3/campaigncreate.func.php

        Optional parameters: segment_opts, type_opts
        """
        # enforce the 100 char limit (urlencoded!!!)
        title = options.get('title', options['subject'])
        if isinstance(title, unicode):
            title = title.encode('utf-8')
        titlelen = len(urllib.quote_plus(title))
        if titlelen > 99:
            title = title[:-(titlelen - 96)] + '...'
            warn("cropped campaign title to fit the 100 character limit, new title: '%s'" % title, ChimpyWarning)
        subject = options['subject']
        if isinstance(subject, unicode):
            subject = subject.encode('utf-8')
        subjlen = len(urllib.quote_plus(subject))
        if subjlen > 99:
            subject = subject[:-(subjlen - 96)] + '...'
            warn("cropped campaign subject to fit the 100 character limit, new subject: '%s'" % subject, ChimpyWarning)
        options['title'] = title
        options['subject'] = subject
        return self._api_call(method='campaignCreate', type=campaign_type, options=options, content=content, **kwargs)

    def campaign_delete(self, cid):
        """Delete a campaign.
        http://www.mailchimp.com/api/1.3/campaigndelete.func.php
        """

        return self._api_call(method='campaignDelete', cid=cid)

    def campaign_pause(self, cid):
        """Pause a RSS campaign from sending.
        http://apidocs.mailchimp.com/api/1.3/campaignpause.func.php
        """

        return self._api_call(method='campaignPause', cid=cid)

    def campaign_replicate(self, cid):
        """Replicate a campaign.
        http://apidocs.mailchimp.com/api/1.3/campaignreplicate.func.php
        """

        return self._api_call(method='campaignReplicate', cid=cid)

    def campaign_resume(self, cid):
        """Resume sending a RSS campaign.
        http://apidocs.mailchimp.com/api/1.3/campaignresume.func.php
        """

        return self._api_call(method='campaignResume', cid=cid)

    def campaign_schedule(self, cid, schedule_time, schedule_time_b=None):
        """Schedule a campaign to be sent in the future.
        http://apidocs.mailchimp.com/api/1.3/campaignschedule.func.php
        """

        schedule_time = transform_datetime(schedule_time)

        if schedule_time_b:
            schedule_time_b = transform_datetime(schedule_time_b)

        return self._api_call(method='campaignSchedule', cid=cid, schedule_time=schedule_time, schedule_time_b=schedule_time_b)

    def campaign_send_now(self, cid):
        """Send a given campaign immediately.
        http://apidocs.mailchimp.com/api/1.3/campaignsendnow.func.php
        """

        return self._api_call(method='campaignSendNow', cid=cid)

    def campaign_send_test(self, cid, test_emails, **kwargs):
        """Send a test of this campaign to the provided email address.
        Optional parameter: send_type
        http://apidocs.mailchimp.com/api/1.3/campaignsendtest.func.php
        """

        if isinstance(test_emails, basestring):
            test_emails = [test_emails]

        return self._api_call(method='campaignSendTest', cid=cid, test_emails=test_emails, **kwargs)

    def templates(self, user=True, gallery=False, base=False):
        """
        Retrieve various templates available in the system, allowing something
        similar to our template gallery to be created.

        http://apidocs.mailchimp.com/api/1.3/templates.func.php
        """
        return self._api_call(method='templates', user=user, gallery=gallery, base=base)

    def template_info(self, template_id, template_type='user'):
        """
        Pull details for a specific template to help support editing
        http://apidocs.mailchimp.com/api/1.3/templateinfo.func.php
        """
        return self._api_call(method='templateInfo', tid=template_id, type=type)

    def campaign_templates(self):
        return self.templates()['user']

    def campaign_unschedule(self, cid):
        """Unschedule a campaign that is scheduled to be sent in the future  """

        return self._api_call(method='campaignUnschedule', cid=cid)

    def campaign_update(self, cid, name, value):
        """Update just about any setting for a campaign that has not been sent.
        http://apidocs.mailchimp.com/api/1.3/campaignupdate.func.php
        """

        return self._api_call(method='campaignUpdate', cid=cid, name=name, value=value)

    def campaigns(self, filter_id='', filter_folder=None, filter_fromname='', filter_fromemail='',
                  filter_title='', filter_subject='', filter_sendtimestart=None, filter_sendtimeend=None,
                  filter_exact=False, start=0, limit=50):
        """Get the list of campaigns and their details matching the specified filters.
        Timestamps should be passed as datetime objects.

        http://apidocs.mailchimp.com/api/1.3/campaigns.func.php
        """

        filter_sendtimestart = transform_datetime(filter_sendtimestart)
        filter_sendtimeend = transform_datetime(filter_sendtimeend)


        return self._api_call(method='campaigns',
                              filter_id=filter_id, filter_folder=filter_folder, filter_fromname=filter_fromname,
                              filter_fromemail=filter_fromemail, filter_title=filter_title, filter_subject=filter_subject,
                              filter_sendtimestart=filter_sendtimestart, filter_sendtimeend=filter_sendtimeend,
                              filter_exact=filter_exact, start=start, limit=limit)

    def campaign_segment_test(self, list_id, options):
        return self._api_call(method='campaignSegmentTest', list_id=list_id, options=options)

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

    # backwars compat for v1.2
    campaign_folders = folders
