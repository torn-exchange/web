# Generated manually on 2026-08-29

from django.db import migrations


JOB = "main.services.schedule.jobs.refresh_market_stats_job.RefreshMarketStatsJob"
RUN_AT = {"x": 0, "every": 10, "period": "minute"}


def create_schedule(apps, schema_editor):
    Schedule = apps.get_model("main", "Schedule")
    Schedule.objects.get_or_create(
        job=JOB,
        defaults={"run_at": RUN_AT, "unique": True, "active": True},
    )


def remove_schedule(apps, schema_editor):
    Schedule = apps.get_model("main", "Schedule")
    Schedule.objects.filter(job=JOB).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0059_receipt_management_changelog_entry"),
    ]

    operations = [
        migrations.RunPython(create_schedule, remove_schedule),
    ]
