"""
Tests for chimpy. Run them with noserunner

You need to activate groups in the Mailchimp web UI before running tests:

 * Browse to http://admin.mailchimp.com
 * List setting -> Groups for segmentation
 * Check "add groups to my list"

"""

import datetime
import functools
import md5
import os
import pprint
import random

import chimpy

chimp = None


EMAIL_ADDRESS = 'casualbear@googlemail.com'
EMAIL_ADDRESS2 = 'dummy@dummy.com'
LIST_NAME = 'unittests'
LIST_ID = None
DEBUG = True


def capture_failures(func):
    """Decorator to assist in processing test failures.

    Raising AssertionErrors part way through test cases leaves the remote list
    in an inconsistent state between test runs, potentially causing other tests
    to fail. For this reason, most tests in here are decorated with this &
    return a list of failures for processing after all cleanup has been
    performed (or at least attempted).

    """
    @functools.wraps(func)
    def _inner(*args, **kwargs):
        failures = func(*args, **kwargs)
        if failures and len(failures):
            raise AssertionError(
                '%s:\n%s' % (func.__name__, '\n'.join(failures))
            )

    return _inner


def check_api_response(failures, result, action):
    """Simple helper to avoid writing repetitive checks."""
    if not result:
        failures.append(
            'falsy result when trying to %s: %s' % (action, str(result))
        )


def log(*args, **kwargs):
    if DEBUG:
        pprint.pprint(*args, **kwargs)


def setup_module():
    global chimp
    key = None
    try:
        from django.conf import settings
        key = settings.MAILCHIMP_API_KEY
    except:
        key = os.environ['MAILCHIMP_APIKEY']

    assert key is not None, (
        "please set the MAILCHIMP_APIKEY environment variable\n"
        "you can get a new api key by calling:\n"
        " wget 'http://api.mailchimp.com/1.1/?output=json&method=login"
        "&password=xxxxxx&username=yyyyyyyy' -O apikey"
    )

    chimp = chimpy.Connection(key)


def test_ping():
    assert chimp.ping() == "Everything's Chimpy!"


def test_lists():
    lists = chimp.lists()
    log(lists)
    list_names = map(lambda x: x['name'], lists)
    assert LIST_NAME in list_names


def list_id():
    global LIST_ID
    if LIST_ID is None:
        test_list = [x for x in chimp.lists() if x['name'] == LIST_NAME].pop()
        LIST_ID = test_list['id']
    return LIST_ID


@capture_failures
def test_list_subscribe_and_unsubscribe():
    failures = []

    # use double_optin=False to prevent manual intervention
    result = chimp.list_subscribe(list_id(), EMAIL_ADDRESS,
                                    {'FIRST': 'unit', 'LAST': 'tests'},
                                    double_optin=False)
    log(result)
    check_api_response(failures, result, 'subscribe')

    members = chimp.list_members(list_id())['data']
    log(members)
    emails = map(lambda x: x['email'], members)
    log(members)

    if EMAIL_ADDRESS not in emails:
        failures.append('email address not found in list')

    result = chimp.list_unsubscribe(list_id(),
                                    EMAIL_ADDRESS,
                                    delete_member=True,
                                    send_goodbye=False,
                                    send_notify=False)
    log(result)
    check_api_response(failures, result, 'unsubscribe')

    return failures


@capture_failures
def test_list_batch_subscribe_and_batch_unsubscribe():
    failures = []

    batch = [{'EMAIL':EMAIL_ADDRESS, 'EMAIL_TYPE':'html'},
             {'EMAIL':EMAIL_ADDRESS2, 'EMAIL_TYPE':'text'}]

    result = chimp.list_batch_subscribe(list_id(),
                                        batch,
                                        double_optin=False,
                                        update_existing=False,
                                        replace_interests=False)

    if result['add_count'] != 2:
        failures.append(
            'expected add_count of 2, got %d' % result.get('add_count')
        )

    members = chimp.list_members(list_id())['data']
    emails = map(lambda x: x['email'], members)

    for item in batch:
        if item.get('EMAIL') not in emails:
            failures.append(
                '%s not in email list members' % item.get('EMAIL')
            )

    result = chimp.list_batch_unsubscribe(
        list_id(), [EMAIL_ADDRESS, EMAIL_ADDRESS2],
        delete_member=True, send_goodbye=False, send_notify=False,
    )

    if result['success_count'] != 2:
        failures.append(
            'expected success_count of 2, got %d' % result.get('success_count')
        )

    return failures


@capture_failures
def test_list_interest_groups_add_and_delete():
    failures = []

    # check no lists exists
#    log(chimp.list_interest_groups(list_id()))
    grouping_id = chimp.list_interest_groupings_add(
        list_id(), 'test grouping', 'hidden', ['first group'],
    )
    if len(chimp.list_interest_groups(list_id(), grouping_id)) != 1:
        failures.append(
            'interest group not found with id %s' % grouping_id
        )

    # add list
    result = chimp.list_interest_group_add(list_id(), 'test', grouping_id)
    check_api_response(failures, result, 'add interest group')

    num_groups = len(chimp.list_interest_groups(list_id(), grouping_id))
    if num_groups != 2:
        failures.append(
            'expected 2 interest groups, got %d' % num_groups
        )

    # delete list
    result = chimp.list_interest_group_del(list_id(), 'test', grouping_id)
    check_api_response(failures, result, 'delete interest group')

    num_groups = len(chimp.list_interest_groups(list_id(), grouping_id))
    if num_groups != 1:
        failures.append(
            'expected 1 interest group, got %d' % num_groups
        )

    result = chimp.list_interest_groupings_del(grouping_id)
    check_api_response(failures, result, 'delete interest groupings')

    return failures


@capture_failures
def test_list_merge_vars_add_and_delete():
    failures = []

    log(chimp.list_merge_vars(list_id()))
    merge_vars_count = len(chimp.list_merge_vars(list_id()))
    if merge_vars_count != 3:
        failures.append(
            'expected 3 merge vars; found %d' % merge_vars_count
        )

    # add list
    result = chimp.list_merge_var_add(list_id(), 'test', 'some_text')
    check_api_response(failures, result, 'add merge var')

    merge_vars_count = len(chimp.list_merge_vars(list_id()))
    if merge_vars_count != 4:
        failures.append(
            'expected 4 merge vars; found %d' % merge_vars_count
        )

    # delete list
    result = chimp.list_merge_var_del(list_id(), 'test')
    check_api_response(failures, result, 'delete merge var')

    merge_vars_count = len(chimp.list_merge_vars(list_id()))
    if merge_vars_count != 3:
        failures.append(
            'expected 3 merge vars; found %d' % merge_vars_count
        )

    return failures


@capture_failures
def test_list_update_member_and_member_info():
    failures = []

    # set up
    result = chimp.list_subscribe(
        list_id(),
        EMAIL_ADDRESS,
        {'FIRST': 'unit', 'LAST': 'tests'},
        double_optin=False
    )
    check_api_response(failures, result, 'subscribe')

    result = chimp.list_merge_var_add(list_id(), 'TEST', 'test_merge_var')
    check_api_response(failures, result, 'add merge var')

    grouping_id = chimp.list_interest_groupings_add(
        list_id(), 'tlistg', 'hidden', ['tlist'],
    )

    # update member and get the info back
    result = chimp.list_update_member(
        list_id(),
        EMAIL_ADDRESS,
        {'TEST': 'abc', 'INTERESTS': 'tlist'},
        replace_interests=False,
    )
    check_api_response(failures, result, 'update member')

    info = chimp.list_member_info(list_id(), EMAIL_ADDRESS)
    log(info)

    # tear down
    result = chimp.list_merge_var_del(list_id(), 'TEST')
    check_api_response(failures, result, 'delete merge var')

    result = chimp.list_interest_group_del(list_id(), 'tlist', grouping_id)
    check_api_response(failures, result, 'delete interest group')

    result = chimp.list_interest_groupings_del(grouping_id)
    check_api_response(failures, result, 'delete interest groupings')

    result = chimp.list_unsubscribe(
        list_id(), EMAIL_ADDRESS,
        delete_member=True, send_goodbye=False, send_notify=False,
    )
    check_api_response(failures, result, 'unsubscribe')

    # check the info matches the set up
    if 'TEST' not in info['merges']:
        failures.append("'TEST' not found in member info")

    if info['merges']['TEST'] != 'abc':
        failures.append('member info inaccurate')

    return failures


def test_create_delete_campaign():
    try:
        uid = md5.new(str(random.random())).hexdigest()
        subject = 'chimpy campaign test %s' % uid
        options = {'list_id': list_id(),
               'subject': subject,
               'from_email': EMAIL_ADDRESS,
               'from_name': 'chimpy',
               'generate_text': True
               }

        #this just to be sure flatten utility is working
        segment_opts = {
            'match': 'any',
            'conditions': [
                {'field': 'date', 'op': 'gt', 'value': '2000-01-01'},
                {'field': 'email', 'op': 'like', 'value': '@'},
            ],
        }

        html = """ <html><body><h1>My test newsletter</h1><p>Just testing</p>
                   <a href="*|UNSUB|*">Unsubscribe</a>*|REWARDS|*</body>"""

        content = {'html': html}
        cid = chimp.campaign_create(
            'regular', options, content, segment_opts=segment_opts,
        )
        assert isinstance(cid, basestring)

        # Filtering by subject doesn't work?
#        campaigns = chimp.campaigns(filter_subject=subject)
#        assert len(campaigns['data'])==1

        # check if the new campaign really is there
        campaign = None
        for c in chimp.campaigns()['data']:
            if c['subject'] == subject:
                assert campaign is None
                campaign = c

        assert campaign['id'] == cid

        # our content properly addd?
        final_content = chimp.campaign_content(cid)
        assert '<h1>My test newsletter</h1>' in final_content['html']
        assert 'My test newsletter' in final_content['text']
    finally:
        # clean up
        chimp.campaign_delete(cid)


def test_replicate_update_campaign():
    """ replicates and updates a campaign """
    try:
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
        assert isinstance(newcid, basestring)

        newsubject = 'Fresh subject ' + uid
        newtitle = 'Custom title ' + uid

        res = chimp.campaign_update(newcid, 'subject', newsubject)
        assert res is True
        res = chimp.campaign_update(newcid, 'title', newtitle)
        assert res is True

#        campaigns = chimp.campaigns(filter_subject=newsubject)
#        log(campaigns['data'])
#        assert len(campaigns['data'])==1
#        campaigns = chimp.campaigns(filter_title=newtitle)
#        assert len(campaigns['data'])==1
    finally:
        chimp.campaign_delete(newcid)
        chimp.campaign_delete(cid)


def test_schedule_campaign():
    """ schedules and unschedules a campaign """
    try:
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

        schedule_time = datetime.datetime(2112, 12, 20, 19, 0, 0)
        chimp.campaign_schedule(cid, schedule_time)

        # Filtering by subject doesn't work?
#        campaign = chimp.campaigns(filter_subject=subject)['data'][0]
        campaign = None
        for c in chimp.campaigns()['data']:
            if c['subject'] == subject:
                assert campaign is None
                campaign = c
        assert campaign['status'] == 'schedule'
        assert campaign['send_time'] in (
            'Dec 20, 2112 07:00 pm', '2112-12-20 19:00:00'
        )

        chimp.campaign_unschedule(cid)
        campaign = chimp.campaigns(filter_subject=subject)['data'][0]
        assert campaign['status'] == 'save'
    finally:
        chimp.campaign_delete(cid)


def test_rss_campaign():
    """ add, pause, resume rss campaign """
    try:
        uid = md5.new(str(random.random())).hexdigest()
        subject = 'chimpy campaign rss test %s' % uid
        options = {'list_id': list_id(),
               'subject': subject,
               'from_email': EMAIL_ADDRESS,
               'from_name': 'chimpy',
               'generate_text': True
               }

        html = """
            <html><body><h1>My test RSS newsletter</h1><p>Just testing</p>
           <a href="*|UNSUB|*">Unsubscribe</a>*|REWARDS|*</body>"""

        content = {'html': html}
        type_opts = {'url': 'http://mailchimp.com/blog/rss'}

        cid = chimp.campaign_create(
            'rss', options, content, type_opts=type_opts
        )
        campaign = chimp.campaigns(filter_subject=subject)['data'][0]
        assert campaign['type'] == 'rss'

        # Todo: Could not find a way to activate the RSS from the API. You need
        # to activate before being able to test pause and resume. send_now and
        # schedule didn't do the trick.

        #chimp.campaign_pause(cid)
        #chimp.campaign_resume(cid)
    finally:
        chimp.campaign_delete(cid)


def test_missing_list_member():
    """Just check the exception is raised correctly"""
    try:
        chimp.list_member_info(list_id(), 'nosuch@example.com')
        assert False
    except chimpy.ChimpyException:
        pass


@capture_failures
def test_one_missing_list_member():
    """Test a multi-email lookup where at least one does exist."""
    chimp.list_subscribe(
        list_id(), EMAIL_ADDRESS,
        {'FIRST': 'unit', 'LAST': 'tests'}, double_optin=False,
    )

    failures = []
    result = None
    email = 'nosuch@example.com'

    try:
        result = chimp.list_member_info(
            list_id(), [email, EMAIL_ADDRESS],
        )
        if not any(map(lambda x: x.get('error', False), result['data'])):
            failures.append('bad email address not raised as error by API')
    except chimpy.ChimpyException:
        failures.append('exception should not have been raised')

    chimp.list_unsubscribe(
        list_id(), EMAIL_ADDRESS,
        delete_member=True, send_goodbye=False, send_notify=False,
    )

    return failures


@capture_failures
def test_partial_batch_unsubscribe():
    """Make sure no exception is raised when some unsubscribes succeed"""
    chimp.list_subscribe(
        list_id(), EMAIL_ADDRESS,
        {'FIRST': 'unit', 'LAST': 'tests'}, double_optin=False,
    )

    failures = []
    try:
        result = chimp.list_batch_unsubscribe(
            list_id(), ['nosuch@example.com', EMAIL_ADDRESS],
            delete_member=True, send_goodbye=False, send_notify=False,
        )

        if result['success_count'] != 1:
            failures.append(
                'expected 1 success, got %d' % result['success_count']
            )
        if result['error_count'] != 1:
            failures.append('expected 1 error, got %d' % result['error_count'])
    except:
        failures.append('exception should not have been raised')
        chimp.list_unsubscribe(
            list_id(), EMAIL_ADDRESS,
            delete_member=True, send_goodbye=False, send_notify=False,
        )

    return failures


def test_bad_batch_unsubscribe():
    try:
        chimp.list_batch_unsubscribe(
            list_id(), ['nosuch@example.com'],
            delete_member=True, send_goodbye=False, send_notify=False,
        )
        assert False
    except chimpy.ChimpyException:
        pass


if __name__ == '__main__':
    setup_module()
    for f in globals().keys():
        if f.startswith('test_') and callable(globals()[f]):
            print f
            globals()[f]()
