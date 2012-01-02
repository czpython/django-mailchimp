# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        pass

    def backwards(self, orm):
        pass

    models = {
        'mailchimp.campaign': {
            'Meta': {'object_name': 'Campaign'},
            'campaign_id': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'sent_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'mailchimp.queue': {
            'Meta': {'object_name': 'Queue'},
            'authenticate': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'auto_footer': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'auto_tweet': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'campaign_type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'contents': ('django.db.models.fields.TextField', [], {}),
            'folder_id': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'from_email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'from_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'generate_text': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'google_analytics': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'list_id': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'segment_options': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'segment_options_all': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'segment_options_conditions': ('django.db.models.fields.TextField', [], {}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'template_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'to_email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'tracking_html_clicks': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'tracking_opens': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'tracking_text_clicks': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'type_opts': ('django.db.models.fields.TextField', [], {})
        },
        'mailchimp.reciever': {
            'Meta': {'object_name': 'Reciever'},
            'campaign': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'recievers'", 'to': "orm['mailchimp.Campaign']"}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }
    
    complete_apps = ['mailchimp']
