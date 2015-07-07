import json

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _
from mailchimp.utils import get_connection


class QueueManager(models.Manager):
    def queue(self, campaign_type, contents, list_id, template_id, subject,
        from_email, from_name, to_email, folder_id=None, tracking_opens=True,
        tracking_html_clicks=True, tracking_text_clicks=False, title=None,
        authenticate=False, google_analytics=None, auto_footer=False,
        auto_tweet=False, segment_options=False, segment_options_all=True,
        segment_options_conditions=[], type_opts={}, obj=None, extra_info=[]):
        """
        Queue a campaign
        """
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



class Queue(models.Model):
    """
    A FIFO queue for async sending of campaigns
    """
    campaign_type = models.CharField(max_length=50)
    contents = models.TextField()
    list_id = models.CharField(max_length=50)
    template_id = models.PositiveIntegerField()
    subject = models.CharField(max_length=255)
    from_email = models.EmailField()
    from_name = models.CharField(max_length=255)
    to_email = models.EmailField()
    folder_id = models.CharField(max_length=50, null=True, blank=True)
    tracking_opens = models.BooleanField(default=True)
    tracking_html_clicks = models.BooleanField(default=True)
    tracking_text_clicks = models.BooleanField(default=False)
    title = models.CharField(max_length=255, null=True, blank=True)
    authenticate = models.BooleanField(default=False)
    google_analytics = models.CharField(max_length=100, blank=True, null=True)
    auto_footer = models.BooleanField(default=False)
    generate_text = models.BooleanField(default=False)
    auto_tweet = models.BooleanField(default=False)
    segment_options = models.BooleanField(default=False)
    segment_options_all = models.BooleanField()
    segment_options_conditions = models.TextField()
    type_opts = models.TextField()
    content_type = models.ForeignKey(ContentType, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = generic.GenericForeignKey('content_type', 'object_id')
    extra_info = models.TextField(null=True)
    locked = models.BooleanField(default=False)
    
    objects = QueueManager()
    
    def send(self):
        """
        send (schedule) this queued object
        """
        # check lock
        if self.locked:
            return False
        # aquire lock
        self.locked = True
        self.save()
        # get connection and send the mails 
        c = get_connection()
        tpl = c.get_template_by_id(self.template_id)
        content_data = dict([(str(k), v) for k,v in json.loads(self.contents).items()])
        built_template = tpl.build(**content_data)
        tracking = {'opens': self.tracking_opens, 
                    'html_clicks': self.tracking_html_clicks,
                    'text_clicks': self.tracking_text_clicks}
        if self.google_analytics:
            analytics = {'google': self.google_analytics}
        else:
            analytics = {}
        segment_opts = {'match': 'all' if self.segment_options_all else 'any',
            'conditions': json.loads(self.segment_options_conditions)}
        type_opts = json.loads(self.type_opts)
        title = self.title or self.subject
        camp = c.create_campaign(self.campaign_type, c.get_list_by_id(self.list_id),
            built_template, self.subject, self.from_email, self.from_name,
            self.to_email, self.folder_id, tracking, title, self.authenticate,
            analytics, self.auto_footer, self.generate_text, self.auto_tweet,
            segment_opts, type_opts)
        if camp.send_now_async():
            self.delete()
            kwargs = {}
            if self.content_type and self.object_id:
                kwargs['content_type'] = self.content_type
                kwargs['object_id'] = self.object_id
            if self.extra_info:
                kwargs['extra_info'] = json.loads(self.extra_info)
            return Campaign.objects.create(camp.id, segment_opts, **kwargs)
        # release lock if failed
        self.locked = False
        self.save()
        return False
    
    def get_dequeue_url(self):
        return reverse('mailchimp_dequeue', kwargs={'id': self.id})
    
    def get_cancel_url(self):
        return reverse('mailchimp_cancel', kwargs={'id': self.id})
    
    def get_list(self):
        return get_connection().lists[self.list_id]
    
    @property
    def object(self):
        """
        The object might have vanished until now, so triple check that it's there!
        """
        if self.object_id:
            model = self.content_type.model_class()
            try:
                return model.objects.get(id=self.object_id)
            except model.DoesNotExist:
                return None
        return None
    
    def get_object_admin_url(self):
        if not self.object:
            return ''
        name = 'admin:%s_%s_change' % (self.object._meta.app_label,
            self.object._meta.module_name)
        return reverse(name, args=(self.object.pk,))
    
    def can_dequeue(self, user):
        if user.is_superuser:
            return True
        if not user.is_staff:
            return False
        if callable(getattr(self.object, 'mailchimp_can_dequeue', None)):
            return self.object.mailchimp_can_dequeue(user)
        return user.has_perm('mailchimp.can_send') and user.has_perm('mailchimp.can_dequeue') 
    

class CampaignManager(models.Manager):
    def create(self, campaign_id, segment_opts, content_type=None, object_id=None,
            extra_info=[]):
        con = get_connection()
        camp = con.get_campaign_by_id(campaign_id)
        extra_info = json.dumps(extra_info)
        obj = self.model(content=camp.content, campaign_id=campaign_id,
             name=camp.title, content_type=content_type, object_id=object_id,
             extra_info=extra_info)
        obj.save()
        segment_opts = dict([(str(k), v) for k,v in segment_opts.items()])
        for email in camp.list.filter_members(segment_opts):
            Reciever.objects.create(campaign=obj, email=email)
        return obj
    
    def get_or_404(self, *args, **kwargs):
        return get_object_or_404(self.model, *args, **kwargs)
    
    
class DeletedCampaign(object):
    subject = u'<deleted from mailchimp>'


class Campaign(models.Model):
    sent_date = models.DateTimeField(auto_now_add=True)
    campaign_id = models.CharField(max_length=50)
    content = models.TextField()
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey(ContentType, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = generic.GenericForeignKey('content_type', 'object_id')
    extra_info = models.TextField(null=True)
    
    objects = CampaignManager()
    
    class Meta:
        ordering = ['-sent_date']
        permissions = [('can_view', 'Can view Mailchimp information'),
                       ('can_send', 'Can send Mailchimp newsletters')]
        verbose_name = _('Mailchimp Log')
        verbose_name_plural = _('Mailchimp Logs')
        
    def get_absolute_url(self):
        return reverse('mailchimp_campaign_info', kwargs={'campaign_id': self.campaign_id})
    
    def get_object_admin_url(self):
        if not self.object:
            return ''
        name = 'admin:%s_%s_change' % (self.object._meta.app_label,
            self.object._meta.module_name)
        return reverse(name, args=(self.object.pk,))
    
    def get_extra_info(self):
        if self.extra_info:
            return json.loads(self.extra_info)
        return []
    
    @property
    def object(self):
        """
        The object might have vanished until now, so triple check that it's there!
        """
        if self.object_id:
            model = self.content_type.model_class()
            try:
                return model.objects.get(id=self.object_id)
            except model.DoesNotExist:
                return None
        return None
    
    @property
    def mc(self):
        try:
            if not hasattr(self, '_mc'):
                self._mc = get_connection().get_campaign_by_id(self.campaign_id)
            return self._mc
        except:
            return DeletedCampaign()


class Reciever(models.Model):
    campaign = models.ForeignKey(Campaign, related_name='recievers')
    email = models.EmailField()