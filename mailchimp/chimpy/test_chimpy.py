"""
Tests for chimpy. Run them with noserunner

You need to activate groups in the Mailchimp web UI before running tests:

 * Browse to http://admin.mailchimp.com
 * List setting -> Groups for segmentation
 * Check "add groups to my list"

"""

import os
import pprint
import operator
import random
import hashlib
import datetime
import six

import chimpy

chimp = None


EMAIL_ADDRESS = 'casualbear@googlemail.com'
EMAIL_ADDRESS2 = 'dummy@dummy.com'
LIST_NAME = 'unittests'
LIST_ID = None


def setup_module():
    assert 'MAILCHIMP_APIKEY' in os.environ, \
        "please set the MAILCHIMP_APIKEY environment variable\n" \
        "you can get a new api key by calling:\n" \
        " wget 'http://api.mailchimp.com/1.1/?output=json&method=login" \
        "&password=xxxxxx&username=yyyyyyyy' -O apikey"

    global chimp
    chimp = chimpy.Connection(os.environ['MAILCHIMP_APIKEY'])


def test_ping():
    assert chimp.ping() == "Everything's Chimpy!"


def test_lists():
    lists = chimp.lists()
    pprint.pprint(lists)
    list_names = map(lambda x: x['name'], lists)
    assert LIST_NAME in list_names


def list_id():
    global LIST_ID
    if LIST_ID is None:
        test_list = [x for x in chimp.lists() if x['name'] == LIST_NAME].pop()
        LIST_ID = test_list['id']
    return LIST_ID

# use double_optin=False to prevent manual intervention
def test_list_subscribe_and_unsubscribe():
    result = chimp.list_subscribe(list_id(), EMAIL_ADDRESS,
                                    {'FIRST': 'unit', 'LAST': 'tests'},
                                    double_optin=False)
    pprint.pprint(result)
    assert result == True

    members = chimp.list_members(list_id())['data']
    print(members)
    emails = map(lambda x: x['email'], members)
    print(members)
    assert EMAIL_ADDRESS in emails

    result = chimp.list_unsubscribe(list_id(),
                                    EMAIL_ADDRESS,
                                    delete_member=True,
                                    send_goodbye=False,
                                    send_notify=False)
    pprint.pprint(result)
    assert result == True

def test_list_batch_subscribe_and_batch_unsubscribe():
    batch = [{'EMAIL':EMAIL_ADDRESS,'EMAIL_TYPE':'html'},
             {'EMAIL':EMAIL_ADDRESS2,'EMAIL_TYPE':'text'}]

    result = chimp.list_batch_subscribe(list_id(),
                                        batch,
                                        double_optin=False,
                                        update_existing=False,
                                        replace_interests=False)
    assert result['add_count'] == 2

    members = chimp.list_members(list_id())['data']
    emails = map(lambda x: x['email'], members)
    assert EMAIL_ADDRESS in emails
    assert EMAIL_ADDRESS2 in emails

    result = chimp.list_batch_unsubscribe(list_id(),
                                          [EMAIL_ADDRESS,EMAIL_ADDRESS2],
                                          delete_member=True,
                                          send_goodbye=False,
                                          send_notify=False)
    assert result['success_count'] == 2

def test_list_interest_groups_add_and_delete():
    # check no lists exists
#    pprint.pprint(chimp.list_interest_groups(list_id()))
    grouping_id = chimp.list_interest_groupings_add(list_id(), 'test grouping', 'hidden', ['first group'])
    assert len(chimp.list_interest_groups(list_id(), grouping_id)['groups']) == 1

    # add list
    assert chimp.list_interest_group_add(list_id(), 'test', grouping_id)
    assert len(chimp.list_interest_groups(list_id(), grouping_id)['groups']) == 2

    # delete list
    assert chimp.list_interest_group_del(list_id(), 'test', grouping_id)
    assert len(chimp.list_interest_groups(list_id(), grouping_id)['groups']) == 1
    assert (chimp.list_interest_groupings_del(grouping_id))

def test_list_merge_vars_add_and_delete():
    pprint.pprint(chimp.list_merge_vars(list_id()))
    assert len(chimp.list_merge_vars(list_id())) == 3

    # add list
    assert chimp.list_merge_var_add(list_id(), 'test', 'some_text')
    assert len(chimp.list_merge_vars(list_id())) == 4

    # delete list
    assert chimp.list_merge_var_del(list_id(), 'test')
    assert len(chimp.list_merge_vars(list_id())) == 3

def test_list_update_member_and_member_info():
    # set up
    assert chimp.list_subscribe(list_id(), EMAIL_ADDRESS,
                                    {'FIRST': 'unit', 'LAST': 'tests'},
                                    double_optin=False)
    assert chimp.list_merge_var_add(list_id(), 'TEST', 'test_merge_var')
    grouping_id = chimp.list_interest_groupings_add(list_id(), 'tlistg', 'hidden', ['tlist'])


    # update member and get the info back
    assert chimp.list_update_member(list_id(), EMAIL_ADDRESS,
                                    {'TEST': 'abc',
                                    'INTERESTS': 'tlist'}, replace_interests=False)
    info = chimp.list_member_info(list_id(), EMAIL_ADDRESS)
    pprint.pprint(info)

    # tear down
    assert chimp.list_merge_var_del(list_id(), 'TEST')
    assert chimp.list_interest_group_del(list_id(), 'tlist', grouping_id)
    assert chimp.list_interest_groupings_del(grouping_id)
    assert chimp.list_unsubscribe(list_id(), EMAIL_ADDRESS,
                                    delete_member=True,
                                    send_goodbye=False,
                                    send_notify=False)

    # check the info matches the set up
    assert 'TEST' in info['merges']
    assert info['merges']['TEST'] == 'abc'


def test_create_delete_campaign():
    uid = hashlib.md5(str(random.random())).hexdigest()
    subject = 'chimpy campaign test %s' % uid
    options = {'list_id': list_id(),
           'subject': subject,
           'from_email': EMAIL_ADDRESS,
           'from_name': 'chimpy',
           'generate_text': True
           }

    #this just to be sure flatten utility is working
    segment_opts = {'match': 'any', 
            'conditions':[{'field': 'date', 'op': 'gt', 'value': '2000-01-01'},
                          {'field': 'email', 'op': 'like', 'value': '@'}]}

    html = """ <html><body><h1>My test newsletter</h1><p>Just testing</p>
               <a href="*|UNSUB|*">Unsubscribe</a>*|REWARDS|*</body>"""


    content = {'html': html}
    cid = chimp.campaign_create('regular', options, content, segment_opts=segment_opts)
    assert isinstance(cid, six.string_types)

    # check if the new campaign really is there
    campaigns = chimp.campaigns(filter_subject=subject)
    assert len(campaigns['data'])==1
    assert campaigns['data'][0]['id'] == cid

    # our content properly addd?
    final_content = chimp.campaign_content(cid)
    assert '<h1>My test newsletter</h1>' in final_content['html']
    assert 'My test newsletter' in final_content['text']

    # clean up
    chimp.campaign_delete(cid)

def test_replicate_update_campaign():
    """ replicates and updates a campaign """

    uid = md5.new(str(random.random())).hexdigest()
    subject = 'chimpy campaign test %s' % uid
    options = {'list_id': list_id(),
           'subject': subject,
           'from_email': EMAIL_ADDRESS,
           'from_name': 'chimpy',
           'generate_text': True
           }

    html = """ <html><body><h1>My test newsletter</h1><p>Just testing</p>
               <a href="*|UNSUB|*">Unsubscribe</a>*|REWARDS|*</body>"""


    content = {'html': html}
    cid = chimp.campaign_create('regular', options, content)

    newcid = chimp.campaign_replicate(cid=cid)
    assert isinstance(newcid, six.string_types)

    newsubject = 'Fresh subject ' + uid
    newtitle = 'Custom title ' + uid

    res = chimp.campaign_update(newcid, 'subject', newsubject)
    assert res is True
    res = chimp.campaign_update(newcid, 'title', newtitle)
    assert res is True

#    campaigns = chimp.campaigns(filter_subject=newsubject)
#    pprint.pprint(campaigns['data'])
#    assert len(campaigns['data'])==1
#    campaigns = chimp.campaigns(filter_title=newtitle)
#    assert len(campaigns['data'])==1

    #clean up
    chimp.campaign_delete(newcid)
    chimp.campaign_delete(cid)

def test_schedule_campaign():
    """ schedules and unschedules a campaign """

    uid = md5.new(str(random.random())).hexdigest()
    subject = 'chimpy campaign schedule test %s' % uid
    options = {'list_id': list_id(),
           'subject': subject,
           'from_email': EMAIL_ADDRESS,
           'from_name': 'chimpy',
           'generate_text': True
           }

    html = """ <html><body><h1>My test newsletter</h1><p>Just testing</p>
               <a href="*|UNSUB|*">Unsubscribe</a>*|REWARDS|*</body>"""


    content = {'html': html}
    cid = chimp.campaign_create('regular', options, content)

    schedule_time = datetime.datetime(2012, 12, 20, 19, 0, 0)
    chimp.campaign_schedule(cid, schedule_time)

    campaign = chimp.campaigns(filter_subject=subject)['data'][0]
    assert campaign['status'] == 'schedule'
    assert campaign['send_time'] in ('Dec 20, 2012 07:00 pm', '2012-12-20 19:00:00')

    chimp.campaign_unschedule(cid)
    campaign = chimp.campaigns(filter_subject=subject)['data'][0]
    assert campaign['status'] == 'save'

    #clean up
    chimp.campaign_delete(cid)

def test_rss_campaign():
    """ add, pause, resume rss campaign """

    uid = md5.new(str(random.random())).hexdigest()
    subject = 'chimpy campaign rss test %s' % uid
    options = {'list_id': list_id(),
           'subject': subject,
           'from_email': EMAIL_ADDRESS,
           'from_name': 'chimpy',
           'generate_text': True
           }

    html = """ <html><body><h1>My test RSS newsletter</h1><p>Just testing</p>
               <a href="*|UNSUB|*">Unsubscribe</a>*|REWARDS|*</body>"""


    content = {'html': html}
    type_opts = {'url': 'http://mailchimp.com/blog/rss'}

    cid = chimp.campaign_create('rss', options, content, type_opts=type_opts)
    campaign = chimp.campaigns(filter_subject=subject)['data'][0]
    assert campaign['type'] == 'rss'

    # Todo: Could not find a way to activate the RSS from the API. You need to
    # activate before being able to test pause and resume. send_now and schedule
    # didn't do the trick.

    #chimp.campaign_pause(cid)
    #chimp.campaign_resume(cid)

    #clean up
    chimp.campaign_delete(cid)

if __name__ == '__main__':
    setup_module()
    for f in globals().keys():
        if f.startswith('test_') and callable(globals()[f]):
            print(f)
            globals()[f]()
