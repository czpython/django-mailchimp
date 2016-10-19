import datetime
import re

from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.views.decorators.csrf import csrf_exempt

from .models import Campaign, Queue
from .settings import WEBHOOK_KEY
from .signals import get_signal
from .utils import BaseView, get_connection


class MailchimpBaseView(BaseView):

    @property
    def connection(self):
        return get_connection()


class MailchimpView(MailchimpBaseView):
    required_permissions = ['mailchimp.can_view']


class Overview(MailchimpView):
    template = 'mailchimp/overview.html'

    def handle_post(self):
        return self.not_allowed()

    def handle_get(self):
        data = {
            'paginator': self.paginate(Campaign.objects.all(), int(self.kwargs.get('page', 1))),
            'queue': Queue.objects.all()
        }
        return self.render_to_response(data)

    def get_page_link(self, page):
        return self.reverse('mailchimp_overview', page=page)


class ScheduleCampaignForObject(MailchimpView):

    def auth_check(self):
        basic = super(ScheduleCampaignForObject, self).auth_check()
        if not basic:
            return basic
        return self.request.user.has_perm('mailchimp.can_send')

    def handle_post(self):
        return self.not_allowed()

    def back(self):
        return self.redirect(self.request.META['HTTP_REFERER'])

    def handle_get(self):
        ct = ContentType.objects.get(pk=self.kwargs['content_type'])
        obj = ct.model_class().objects.get(pk=self.kwargs['pk'])
        if obj.mailchimp_schedule(self.connection):
            self.message_success("The Campaign has been scheduled for sending.")
        else:
            self.message_error("An error has occured while trying to send, please try again later.")
        return self.back()


class TestCampaignForObjectReal(ScheduleCampaignForObject):

    def handle_get(self):
        ct = ContentType.objects.get(pk=self.kwargs['content_type'])
        obj = ct.model_class().objects.get(pk=self.kwargs['pk'])
        self.connection.warnings.reset()
        if obj.mailchimp_test(self.connection, self.request):
            self.message_success("A Test Campaign has been sent to your email address (%s)." % self.request.user.email)
            for message, category, filename, lineno in self.connection.warnings.get():
                self.message_warning("%s: %s" % (category.__name__, message))
        else:
            self.message_error("And error has occured while trying to send the test mail to you, please try again later")
        return self.json(True)

    
class TestCampaignForObject(ScheduleCampaignForObject):
    template = 'mailchimp/send_test.html'
    
    def handle_get(self):
        referer = self.request.META.get('HTTP_REFERER') or '/'
        data = {
            'ajaxurl': reverse('mailchimp_real_test_for_object', kwargs=self.kwargs),
            'redirecturl': referer,
        }
        return self.render_to_response(data)


class CampaignInformation(MailchimpView):
    template = 'mailchimp/campaign_information.html'

    def handle_post(self):
        return self.not_allowed()

    def handle_get(self):
        camp = Campaign.objects.get_or_404(campaign_id=self.kwargs['campaign_id'])
        data = {'campaign': camp}
        extra_info = camp.get_extra_info()
        if camp.object and hasattr(camp.object, 'mailchimp_get_extra_info'):
            extra_info = camp.object.mailchimp_get_extra_info()
        data['extra_info'] = extra_info
        return self.render_to_response(data)
        

class WebHook(MailchimpBaseView):

    def handle_get(self):
        return self.response("hello chimp")

    def handle_post(self):
        if self.kwargs.get('key', '') != WEBHOOK_KEY:
            return self.not_found()
        data = self.request.POST
        signal = get_signal(data['type'])
        ts = data["fired_at"]
        fired_at = datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
        kwargs = {
            'list': self.connection.get_list_by_id(data["data[list_id]"]),
            'fired_at': fired_at,
            'type': data['type'],
        }
        if data['type'] == 'cleaned':
            kwargs.update({
                'reason': data['data[reason]'],
                'email': data['data[email]'],
            })
        elif data['type'] == 'upemail':
            kwargs.update({
                 'old_email': data['data[old_email]'],
                 'new_email': data['data[new_email]'],
            })
        elif data['type'] == 'campaign':
            kwargs.update({
                'campaign_id': data['data[id]'],
                'subject': data['data[subject]'],
                'status': data['data[status]'],
                'reason': data['data[reason]'],
            })
        else:
            merge_re = re.compile('data\[merges\]\[(?P<name>\w+)\]')
            merges = {}
            for key, value in data.items():
                match = merge_re.match(key)
                if match:
                    name = match.group('name').lower()
                    if name in ('interests', 'fname', 'lname'):
                        continue
                    merges[name] = value
            kwargs.update({
                'email': data['data[email]'],
                'fname': data['data[merges][FNAME]'] if 'data[merges][FNAME]' in data else '',
                'lname': data['data[merges][LNAME]'] if 'data[merges][LNAME]' in data else '',
                'merges': merges,
            })
            if 'data[merges][INTERESTS]' in data:
                kwargs['interests'] = [i.strip() for i in data['data[merges][INTERESTS]'].split(',')]
        signal.send(sender=self.connection, **kwargs)
        return self.response("ok")

        
class Dequeue(ScheduleCampaignForObject):

    def handle_get(self):
        q = Queue.objects.get_or_404(pk=self.kwargs['id'])
        if q.send():
            self.message_success("The Campaign has successfully been dequeued.")
        else:
            self.message_error("An error has occured while trying to dequeue this campaign, please try again later.")
        return self.back()
        

class Cancel(ScheduleCampaignForObject):

    def handle_get(self):
        q = Queue.objects.get_or_404(pk=self.kwargs['id'])
        q.delete()
        self.message_success("The Campaign has been canceled.")
        return self.back()


webhook = csrf_exempt(WebHook())
dequeue = Dequeue()
cancel = Cancel()
campaign_information = CampaignInformation()
overview = Overview()
schedule_campaign_for_object = ScheduleCampaignForObject()
test_campaign_for_object = TestCampaignForObject()
test_real = TestCampaignForObjectReal()
