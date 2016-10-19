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
            name='from_email',
            field=models.EmailField(max_length=254),
        ),
        migrations.AlterField(
            model_name='queue',
            name='to_email',
            field=models.EmailField(max_length=254),
        ),
        migrations.AlterField(
            model_name='reciever',
            name='email',
            field=models.EmailField(max_length=254),
        ),
    ]
