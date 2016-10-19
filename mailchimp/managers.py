import json

from django.contrib.contenttypes.models import ContentType
from django.db.models import Manager
from django.shortcuts import get_object_or_404


class CampaignManager(Manager):

    def create(self, campaign_id, segment_opts, content_type=None, object_id=None,
            extra_info=()):
        from .utils import get_connection

        con = get_connection()
        camp = con.get_campaign_by_id(campaign_id)
        extra_info = json.dumps(extra_info)
        obj = self.model(content=camp.content, campaign_id=campaign_id,
             name=camp.title, content_type=content_type, object_id=object_id,
             extra_info=extra_info)
        obj.save()

        segment_opts = dict([(str(k), v) for k,v in segment_opts.items()])

        for email in camp.list.filter_members(segment_opts):
            obj.receivers.create(email=email)
        return obj

    def get_or_404(self, *args, **kwargs):
        return get_object_or_404(self.model, *args, **kwargs)


class QueueManager(Manager):

    def queue(self, campaign_type, contents, list_id, template_id, subject,
        from_email, from_name, to_name, folder_id=None, tracking_opens=True,
        tracking_html_clicks=True, tracking_text_clicks=False, title=None,
        authenticate=False, google_analytics=None, auto_footer=False,
        auto_tweet=False, segment_options=False, segment_options_all=True,
        segment_options_conditions=(), type_opts=None, obj=None, extra_info=()):
        """
        Queue a campaign
        """
        if not type_opts:
            type_opts = {}

        kwargs = locals().copy()
        kwargs['segment_options_conditions'] = json.dumps(segment_options_conditions)
        kwargs['type_opts'] = json.dumps(type_opts)
        kwargs['contents'] = json.dumps(contents)
        kwargs['extra_info'] = json.dumps(extra_info)
        for thing in ('template_id', 'list_id'):
            thingy = kwargs[thing]
            if hasattr(thingy, 'id'):
                kwargs[thing] = thingy.id
        del kwargs['self']
        del kwargs['obj']
        if obj:
            kwargs['object_id'] = obj.pk
            kwargs['content_type'] = ContentType.objects.get_for_model(obj)
        kwargs['to_email'] = kwargs.pop('to_name')
        return self.create(**kwargs)

    def dequeue(self, limit=None):
        if limit:
            qs = self.filter(locked=False)[:limit]
        else:
            qs = self.filter(locked=False)
        for obj in qs:
             yield obj.send()

    def get_or_404(self, *args, **kwargs):
        return get_object_or_404(self.model, *args, **kwargs)
