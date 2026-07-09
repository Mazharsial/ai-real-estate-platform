# n8n Automation — Daily Deal Scan (Module 15)

This folder holds the **n8n agent** for the platform's automation module.

## What it does
`daily-deal-scan.workflow.json` runs once a day (default **8:00 AM**, cron `0 8 * * *`) and calls
the platform API:

```
GET /api/monitor/scan?city=Dallas&min_under=12&min_score=70
```

The API then:
1. Runs a fresh search + analysis for the city,
2. Flags **new** undervalued / high-score deals and records them as **alerts**,
3. **Emails** every user whose alert-enabled **saved search** matches the new deals
   (see `app/services/monitor.py → notify_subscribers`).

The workflow's `IF` node + sticky note show where you can bolt on **extra** notifications
(Slack, Telegram, a webhook, or appending to a Google Sheet) using `{{ $json.deals }}` and
`{{ $json.email_text }}`.

## How to use it
1. Run n8n (e.g. `npx n8n` or the n8n Desktop app) → open `http://localhost:5678`.
2. **Workflows → Import from File →** choose `daily-deal-scan.workflow.json`.
3. Open the **"Run deal scan (API)"** node and set the URL to your API host
   (local dev: `http://localhost:8000`; Docker: `http://api:8000`; prod: your domain).
4. Click **Execute Workflow** to test, then toggle **Active** to run it on schedule.

> No n8n? You don't need it — the same endpoint works from any cron/scheduler
> (e.g. Windows Task Scheduler, `curl` in a cron job). n8n just gives you a visual,
> extensible version with easy add-on notifications.
