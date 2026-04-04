from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0047_schedule_unique'),
    ]

    operations = [
        migrations.AddField(
            model_name='listing',
            name='effective_price',
            field=models.BigIntegerField(null=True),
        ),
    ]
