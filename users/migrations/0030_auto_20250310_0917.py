# Generated by Django 3.2.25 on 2025-03-10 09:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0029_settings_trade_global_fee'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='settings',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
    ]
