# Generated by Django 3.2.25 on 2025-03-11 11:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0030_auto_20250310_0917'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='api_key',
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
    ]
