# Generated by Django 3.2.25 on 2025-03-10 23:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0040_auto_20250310_2044'),
    ]

    operations = [
        migrations.AlterField(
            model_name='itemvariation',
            name='price',
            field=models.BigIntegerField(null=True),
        ),
    ]
