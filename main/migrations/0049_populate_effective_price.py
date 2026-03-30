from django.db import migrations, models


class Migration(migrations.Migration):
    """Widen effective_price from integer to bigint (0048 created it as integer)."""

    dependencies = [
        ('main', '0048_listing_effective_price'),
    ]

    operations = [
        migrations.AlterField(
            model_name='listing',
            name='effective_price',
            field=models.BigIntegerField(null=True),
        ),
        migrations.RunSQL(
            sql='ALTER TABLE main_listing ALTER COLUMN effective_price TYPE bigint',
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
