import importlib
import warnings

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .exceptions import MailchimpWarning


def get_callable(string_to_callable):
    module_name, object_name = string_to_callable.rsplit('.', 1)
    module = importlib.import_module(module_name)
    return getattr(module, object_name)


API_KEY = getattr(settings, 'MAILCHIMP_API_KEY', None)

if API_KEY is None:
    raise ImproperlyConfigured('django-mailchimp requires the MAILCHIMP_API_KEY setting')

SECURE = getattr(settings, 'MAILCHIMP_SECURE', True)

REAL_CACHE = False
CACHE_TIMEOUT = getattr(settings, 'MAILCHIMP_CACHE_TIMEOUT', 300)

WEBHOOK_KEY = getattr(settings, 'MAILCHIMP_WEBHOOK_KEY', '')
if not WEBHOOK_KEY:
    warnings.warn("you did not define a MAILCHIMP_WEBHOOK_KEY setting. "
        "django-mailchimp will create a random one by itself", MailchimpWarning)
    import string
    import random
    alphanum = string.ascii_letters + string.digits
    for x in range(50):
        WEBHOOK_KEY += random.choice(alphanum)

VIEWS_OVERVIEW = getattr(settings, 'MAILCHIMP_VIEWS_OVERVIEW', 'mailchimp.views.overview')

if not callable(VIEWS_OVERVIEW):
    VIEWS_OVERVIEW = get_callable(VIEWS_OVERVIEW)

VIEWS_INFO = getattr(settings, 'MAILCHIMP_VIEWS_INFO', 'mailchimp.views.campaign_information')

if not callable(VIEWS_INFO):
    VIEWS_INFO = get_callable(VIEWS_INFO)

VIEWS_SCHEDULE_OBJECT = getattr(settings, 'MAILCHIMP_VIEWS_SEND_OBJECT', 'mailchimp.views.schedule_campaign_for_object')

if not callable(VIEWS_SCHEDULE_OBJECT):
    VIEWS_SCHEDULE_OBJECT = get_callable(VIEWS_SCHEDULE_OBJECT)

VIEWS_TEST_OBJECT = getattr(settings, 'MAILCHIMP_VIEWS_TEST_OBJECT', 'mailchimp.views.test_campaign_for_object')

if not callable(VIEWS_TEST_OBJECT):
    VIEWS_TEST_OBJECT = get_callable(VIEWS_TEST_OBJECT)
