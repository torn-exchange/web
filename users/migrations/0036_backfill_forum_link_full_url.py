from django.db import migrations


def backfill_full_forum_urls(apps, schema_editor):
    Settings = apps.get_model('users', 'Settings')
    stale = Settings.objects.exclude(link_to_forum_post__isnull=True).exclude(
        link_to_forum_post__exact='').exclude(
        link_to_forum_post__istartswith='http://').exclude(
        link_to_forum_post__istartswith='https://')

    for settings in stale.iterator():
        settings.link_to_forum_post = f'https://www.torn.com/{settings.link_to_forum_post.lstrip("/")}'
        settings.save(update_fields=['link_to_forum_post'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0035_remove_settings_trade_global_fee'),
    ]

    operations = [
        migrations.RunPython(backfill_full_forum_urls, noop_reverse),
    ]
