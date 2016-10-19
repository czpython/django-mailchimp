# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='Campaign',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('sent_date', models.DateTimeField(auto_now_add=True)),
                ('campaign_id', models.CharField(max_length=50)),
                ('content', models.TextField()),
                ('name', models.CharField(max_length=255)),
                ('object_id', models.PositiveIntegerField(null=True, blank=True)),
                ('extra_info', models.TextField(null=True)),
                ('content_type', models.ForeignKey(blank=True, to='contenttypes.ContentType', null=True)),
            ],
            options={
                'ordering': ['-sent_date'],
                'verbose_name': 'Mailchimp Log',
                'verbose_name_plural': 'Mailchimp Logs',
                'permissions': [('can_view', 'Can view Mailchimp information'), ('can_send', 'Can send Mailchimp newsletters')],
            },
        ),
        migrations.CreateModel(
            name='Queue',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('campaign_type', models.CharField(max_length=50)),
                ('contents', models.TextField()),
                ('list_id', models.CharField(max_length=50)),
                ('template_id', models.PositiveIntegerField()),
                ('subject', models.CharField(max_length=255)),
                ('from_email', models.EmailField(max_length=75)),
                ('from_name', models.CharField(max_length=255)),
                ('to_email', models.EmailField(max_length=75)),
                ('folder_id', models.CharField(max_length=50, null=True, blank=True)),
                ('tracking_opens', models.BooleanField(default=True)),
                ('tracking_html_clicks', models.BooleanField(default=True)),
                ('tracking_text_clicks', models.BooleanField(default=False)),
                ('title', models.CharField(max_length=255, null=True, blank=True)),
                ('authenticate', models.BooleanField(default=False)),
                ('google_analytics', models.CharField(max_length=100, null=True, blank=True)),
                ('auto_footer', models.BooleanField(default=False)),
                ('generate_text', models.BooleanField(default=False)),
                ('auto_tweet', models.BooleanField(default=False)),
                ('segment_options', models.BooleanField(default=False)),
                ('segment_options_all', models.BooleanField()),
                ('segment_options_conditions', models.TextField()),
                ('type_opts', models.TextField()),
                ('object_id', models.PositiveIntegerField(null=True, blank=True)),
                ('extra_info', models.TextField(null=True)),
                ('locked', models.BooleanField(default=False)),
                ('content_type', models.ForeignKey(blank=True, to='contenttypes.ContentType', null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Reciever',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('email', models.EmailField(max_length=75)),
                ('campaign', models.ForeignKey(related_name='recievers', to='mailchimp.Campaign')),
            ],
        ),
    ]
