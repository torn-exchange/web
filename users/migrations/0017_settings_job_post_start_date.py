# Generated by Django 3.0.8 on 2020-08-24 14:58

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0016_auto_20200824_1540'),
    ]

    operations = [
        migrations.AddField(
            model_name='settings',
            name='job_post_start_date',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
