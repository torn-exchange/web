# Generated by Django 3.0.8 on 2020-08-23 13:25
from django.db import migrations, models
import main.models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0024_auto_20200823_1425'),
    ]

    operations = [
         migrations.AlterField(
            model_name='tradereceipt',
            name='receipt_url_string',
            field=models.CharField(default=main.models.generate_url_string, max_length=10, unique=True),
        ),
    ]
