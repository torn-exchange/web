# Generated by Django 3.0.8 on 2020-11-09 16:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0018_profile_work_stats_total'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='te_plus_days',
            field=models.IntegerField(null=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='te_plus_status',
            field=models.BooleanField(default=False),
        ),
    ]
