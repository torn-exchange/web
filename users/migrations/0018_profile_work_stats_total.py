# Generated by Django 3.0.8 on 2020-08-24 18:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0017_settings_job_post_start_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='work_stats_total',
            field=models.IntegerField(null=True),
        ),
    ]
