# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mailchimp', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='queue',
            name='segment_options_all',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='reciever',
            name='campaign',
            field=models.ForeignKey(related_name='receivers', to='mailchimp.Campaign'),
        ),
    ]
