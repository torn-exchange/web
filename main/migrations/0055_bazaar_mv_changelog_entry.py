# Generated manually on 2026-08-08

from django.db import migrations


CHANGELOG_TEXT = (
    "TE Market Value now also factors in bazaar averages (in addition to Torn's "
    "market value and our own item-market price), giving a more accurate lowest-of-three "
    "estimate. Existing discount-based prices were automatically rebalanced so your "
    "effective price didn't change -- but since bazaar averages are usually the lowest "
    "of the three, it's worth reviewing your profit margins on the edit prices page."
)


def create_changelog_entry(apps, schema_editor):
    ChangeLog = apps.get_model('main', 'ChangeLog')
    ChangeLog.objects.get_or_create(description=CHANGELOG_TEXT)


def remove_changelog_entry(apps, schema_editor):
    ChangeLog = apps.get_model('main', 'ChangeLog')
    ChangeLog.objects.filter(description=CHANGELOG_TEXT).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0054_item_item_id_unique_constraint'),
    ]

    operations = [
        migrations.RunPython(create_changelog_entry, remove_changelog_entry),
    ]
