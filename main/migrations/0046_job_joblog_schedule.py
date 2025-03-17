# Generated by Django 3.2.25 on 2025-03-13 17:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0045_itemvariation_market_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='Job',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('job', models.CharField(max_length=250)),
                ('queue', models.CharField(max_length=250)),
                ('payload', models.JSONField(null=True)),
                ('attempts', models.IntegerField(default=0)),
                ('reserved_at', models.DateTimeField(null=True)),
                ('available_at', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='JobLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('job', models.CharField(max_length=250)),
                ('status', models.CharField(max_length=30)),
                ('message', models.JSONField(null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Schedule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('job', models.CharField(max_length=250)),
                ('payload', models.JSONField(null=True)),
                ('run_at', models.JSONField()),
                ('active', models.BooleanField(default=True)),
                ('runnable', models.BooleanField(default=True)),
                ('last_ran_at', models.DateTimeField(null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
