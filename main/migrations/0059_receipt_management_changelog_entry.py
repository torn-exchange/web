# Generated manually on 2026-08-09

from django.db import migrations


CHANGELOG_TEXT = (
    "New: Receipt Management page lets you search every trade receipt you've ever been "
    "part of, as buyer or seller, by trader name, item and quantity, date range, or amount "
    "-- results are tagged Buyer/Seller. Includes a receipts-over-time chart and a per-item "
    "quantity chart when searching by item name."
)


def create_changelog_entry(apps, schema_editor):
    ChangeLog = apps.get_model('main', 'ChangeLog')
    ChangeLog.objects.get_or_create(description=CHANGELOG_TEXT)


def remove_changelog_entry(apps, schema_editor):
    ChangeLog = apps.get_model('main', 'ChangeLog')
    ChangeLog.objects.filter(description=CHANGELOG_TEXT).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0058_receipt_total_amount'),
    ]

    operations = [
        migrations.RunPython(create_changelog_entry, remove_changelog_entry),
    ]
