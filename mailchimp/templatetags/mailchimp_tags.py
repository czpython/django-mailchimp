from django import template
from django.contrib.contenttypes.models import ContentType
from django.conf import settings

from ..utils import is_queued_or_sent


register = template.Library()


def mailchimp_send_for_object(context, object):
    is_sent = is_queued_or_sent(object)
    sent_date = None
    campaign_id = None
    if is_sent and hasattr(is_sent, 'sent_date'):
        sent_date = is_sent.sent_date
        campaign_id = is_sent.campaign_id
    if hasattr(object, 'mailchimp_allow_send'):
        objchck = object.mailchimp_allow_send
    else:
        objchck = lambda r: True
    request = context['request']
    return {
        'content_type': ContentType.objects.get_for_model(object).pk,
        'primary_key': object.pk,
        'allow': request.user.has_perm('mailchimp.can_send') and objchck(request),
        'is_sent': is_sent,
        'sent_date': sent_date,
        'campaign_id': campaign_id,
        'can_view': sent_date and request.user.has_perm('mailchimp.can_view'),
        'admin_prefix': getattr(settings, 'ADMIN_MEDIA_PREFIX', None) or ''.join([settings.STATIC_URL, 'admin/']),
        'can_test': bool(request.user.email),
    }
register.inclusion_tag('mailchimp/send_button.html', takes_context=True)(mailchimp_send_for_object)
