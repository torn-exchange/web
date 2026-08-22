# Monitoring & observability (New Relic)

Account: "Torn Exchange Main" (EU region — use `api.eu.newrelic.com/graphql` for NerdGraph queries, not the default US endpoint). Free tier: 100GB/month data ingest, resets each billing cycle.

## Page / API call counts (already works, no code needed)

New Relic's Python APM agent (`newrelic.ini`, wrapped around WSGI in `torntrades/wsgi.py`) already tracks a transaction per view/API function, including a call count. No custom instrumentation is needed for "how many times was each page/endpoint called" — query it directly:

```sql
SELECT count(*) FROM Transaction WHERE appName = 'Torn Exchange' FACET name SINCE 1 day ago LIMIT 50
```

Run this in the New Relic "Query your data" UI, or save it as a dashboard tile. `name` values look like `WebTransaction/Function/main.views:price_list` or `WebTransaction/Function/main.api:listings`.

## Cron job visibility

Every cron-invoked management command now reports to New Relic in two ways:

1. **APM transaction** — via `main/services/monitoring/cron_command.py`. Single-shot commands (`update_items2`, `update_properties`, `check_player_stats`, `check_online_status`, `check_job_listings`, `clean_names`, `clean_stale_listings`, `delete_old_keys`, `run_jobs`) subclass `MonitoredCommand` instead of `BaseCommand`, which wraps the run in `newrelic.agent.BackgroundTask(..., group="Cron")`. Daemon-loop commands (`run_schedules`, `run_job_queues`) instead call `run_monitored(name, func, ...)` once per loop iteration/dispatch, so each pass shows as its own transaction rather than one never-ending one.
2. **Structured log line** — a `cron` logger (`logging.getLogger("cron")`) emits `cron.start` / `cron.success` (with `duration_ms`) / `cron.failure` (with a stack trace) as JSON. These are written to the same file as `django`'s WARNING+ output (`ERROR_LOG`/`500_ERRORS_FILE` env var), which the server's New Relic Infrastructure agent already tails and forwards — no server-side log-forwarding config changes needed.

Query examples:

```sql
-- All cron activity in the last hour
SELECT * FROM Log WHERE message LIKE '%cron.%' SINCE 1 hour ago

-- Just failures, faceted by which command failed
SELECT count(*) FROM Log WHERE message = 'cron.failure' FACET cron_command SINCE 1 day ago

-- APM transactions for cron runs
SELECT * FROM Transaction WHERE appName = 'Torn Exchange' AND name LIKE 'Cron/%' SINCE 1 hour ago
```

`JobLog` (Postgres table, `main/models.py`) is also now populated consistently for every job dispatched through `run_jobs.py`'s queue (`started`/`success`/`failed` rows) — this is a DB-level backstop independent of New Relic, queryable even if New Relic is down or you haven't looked at it:

```python
JobLog.objects.filter(job='ImportBazaarRW').order_by('-created_at')
```

## Enabling log-to-trace correlation (manual, server-side)

`newrelic.ini` (gitignored — exists both locally and on the server, must be edited in both places, then the app process restarted) currently has `application_logging.*` settings commented out. To let New Relic link a slow/erroring cron transaction directly to its log lines, uncomment and set:

```ini
application_logging.enabled = true
application_logging.forwarding.enabled = true
application_logging.local_decorating.enabled = true
application_logging.metrics.enabled = true
```

Without this, cron logs and cron APM transactions still both show up in New Relic — they just aren't automatically cross-linked in the UI.

## Follow-up: alerting (not set up yet — needs your input)

Only one alert policy currently exists ("Golden Signals", New Relic's auto-onboarding default) and it isn't wired to anything cron-related. Recommended conditions to add later, once you're ready:

- **Cron failure**: alert when `SELECT count(*) FROM Log WHERE message = 'cron.failure'` is nonzero in a short window (e.g. 5 minutes), faceted by `cron_command` so you know which one failed.
- **Cron silence** ("it didn't run" is different from "it failed and told us"): a loss-of-signal / gap-fill alert condition on `Transaction` events named `Cron/<command>`, tuned to each command's expected schedule interval (e.g. alert if no `Cron/check_online_status` transaction appears for 20 minutes when it's expected every 10).

Setting these up requires picking thresholds/notification channels — happy to walk through this in the New Relic UI together when you're ready.

## Follow-up: ingest volume review (not done yet)

Current usage is comfortably under the 100GB/month free cap (~20.75GB/month as of this writing), but most of the forwarded log volume is generic OS/webserver noise rather than app signal:

- Webserver access logs — ~78K lines/day combined
- OS-level logs (auth/syslog) — ~68K lines/day combined
- Django `WARNING` output — ~11K lines/day (a sample showed mostly routine 404s from bot/crawler traffic, e.g. `/prices/Xenocide/`, not real errors)

Cron instrumentation added here contributes comparatively little (a few thousand lines/day across ~9 commands) and won't meaningfully affect the cap by itself. As traffic grows, apache access-log forwarding is the likely long-term driver of ingest volume — worth revisiting whether all of it needs to be forwarded, and whether the Django WARNING threshold/noisy 404s should be tuned down. Also worth confirming how the free-tier account behaves if 100GB/month is ever exceeded (drop vs. bill), since there may be no credit card on file.
