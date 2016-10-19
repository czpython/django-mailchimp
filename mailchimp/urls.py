from django.conf.urls import url

from .settings import VIEWS_INFO, VIEWS_OVERVIEW, VIEWS_SCHEDULE_OBJECT, VIEWS_TEST_OBJECT
from .views import webhook, dequeue, cancel, test_real


urlpatterns = [
    url(r'^$', VIEWS_OVERVIEW, name='mailchimp_overview', kwargs={'page':'1'}),
    url(r'^(?P<page>\d+)/$', VIEWS_OVERVIEW, name='mailchimp_overview'),
    url(r'^send/(?P<content_type>\d+)/(?P<pk>\d+)/$', VIEWS_SCHEDULE_OBJECT, name='mailchimp_schedule_for_object'),
    url(r'^test/(?P<content_type>\d+)/(?P<pk>\d+)/$', VIEWS_TEST_OBJECT, name='mailchimp_test_for_object'),
    url(r'^test/(?P<content_type>\d+)/(?P<pk>\d+)/real/$', test_real, name='mailchimp_real_test_for_object'),
    url(r'^info/(?P<campaign_id>\w+)/$', VIEWS_INFO, name='mailchimp_campaign_info'),
    url(r'^dequeue/(?P<id>\d+)/', dequeue, name='mailchimp_dequeue'),
    url(r'^cancel/(?P<id>\d+)/', cancel, name='mailchimp_cancel'),
    url(r'^webhook/(?P<key>\w+)/', webhook, name='mailchimp_webhook'),
]
