# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Reciever.email'
        db.alter_column(u'mailchimp_reciever', 'email', self.gf('django.db.models.fields.EmailField')(max_length=254))

        # Changing field 'Queue.from_email'
        db.alter_column(u'mailchimp_queue', 'from_email', self.gf('django.db.models.fields.EmailField')(max_length=254))

        # Changing field 'Queue.to_email'
        db.alter_column(u'mailchimp_queue', 'to_email', self.gf('django.db.models.fields.EmailField')(max_length=254))

    def backwards(self, orm):

        # Changing field 'Reciever.email'
        db.alter_column(u'mailchimp_reciever', 'email', self.gf('django.db.models.fields.EmailField')(max_length=75))

        # Changing field 'Queue.from_email'
        db.alter_column(u'mailchimp_queue', 'from_email', self.gf('django.db.models.fields.EmailField')(max_length=75))

        # Changing field 'Queue.to_email'
        db.alter_column(u'mailchimp_queue', 'to_email', self.gf('django.db.models.fields.EmailField')(max_length=75))

    models = {
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'mailchimp.campaign': {
            'Meta': {'ordering': "['-sent_date']", 'object_name': 'Campaign'},
            'campaign_id': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'extra_info': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'sent_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        u'mailchimp.queue': {
            'Meta': {'object_name': 'Queue'},
            'authenticate': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'auto_footer': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'auto_tweet': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'campaign_type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'contents': ('django.db.models.fields.TextField', [], {}),
            'extra_info': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'folder_id': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'from_email': ('django.db.models.fields.EmailField', [], {'max_length': '254'}),
            'from_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'generate_text': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'google_analytics': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'list_id': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'locked': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'segment_options': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'segment_options_all': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'segment_options_conditions': ('django.db.models.fields.TextField', [], {}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'template_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'to_email': ('django.db.models.fields.EmailField', [], {'max_length': '254'}),
            'tracking_html_clicks': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'tracking_opens': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'tracking_text_clicks': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'type_opts': ('django.db.models.fields.TextField', [], {})
        },
        u'mailchimp.reciever': {
            'Meta': {'object_name': 'Reciever'},
            'campaign': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'receivers'", 'to': u"orm['mailchimp.Campaign']"}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '254'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['mailchimp']