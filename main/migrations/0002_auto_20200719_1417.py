# Generated by Django 3.0.8 on 2020-07-19 13:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='item',
            name='weapon_type',
            field=models.CharField(max_length=250, null=True),
        ),
    ]
