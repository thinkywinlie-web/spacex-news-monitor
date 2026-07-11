# SpaceX News Monitor

Automatically tracks SpaceX-related news headlines and their sentiment over time.

## What it does

`spacex_monitor.py`:

1. Pulls headlines from a mix of RSS feeds:
   - **Mainstream**: Reuters Tech, BBC Business, CNBC Tech, NPR Business, The Guardian Space
   - **Niche/space press**: SpaceNews, NASASpaceflight, Space.com, Ars Technica Space, Teslarati Space, Spaceflight Now, Payload Space, The Verge Space
   - **Catch-all search feeds**: Google News (SpaceX, Starship) and Bing News (SpaceX), scoped to the last day
2. Filters the mainstream/niche feeds to entries whose title or summary mentions `spacex`, `starship`, `falcon 9`, `falcon heavy`, or `elon musk` (case-insensitive). The search feeds are already query-scoped, so they aren't filtered further.
3. Scores each headline's sentiment with `vaderSentiment`. A compound score `>= 0.25` is labeled `positive`, `<= -0.25` is `negative`, otherwise `neutral`.
4. Dedupes against `seen_links.json` so re-running the script never re-logs the same article.
5. Appends new rows to `spacex_news_log.csv` with columns: `fetched_at_utc, source, published, title, link, sentiment_score, sentiment_label`.

## Running locally

```bash
pip install -r requirements.txt
python spacex_monitor.py
```

This creates/updates `spacex_news_log.csv` and `seen_links.json` in the project directory.

## Automated schedule

`.github/workflows/monitor.yml` runs the script automatically on GitHub Actions:

- **Trigger**: a cron schedule of `*/30 * * * *` (every 30 minutes, UTC), plus a manual `workflow_dispatch` trigger for on-demand runs.
- **Steps**: checks out the repo, sets up Python 3.11, installs `requirements.txt`, and runs `spacex_monitor.py`.
- **Persistence**: if `spacex_news_log.csv` or `seen_links.json` changed, the workflow commits and pushes them back to the repo using a bot identity (`github-actions[bot]`). The commit message includes `[skip ci]` to avoid re-triggering other workflows. If nothing changed, no commit is made.

Note: GitHub Actions cron schedules are not guaranteed to run at the exact minute — they can be delayed during periods of high load.
