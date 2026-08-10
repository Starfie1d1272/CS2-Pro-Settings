# Contributing

Thanks for helping keep professional CS2 settings tracking alive. The
**most valuable contribution you can make is a fresh HLTV Top 30 ranking
snapshot** — no scraper, no code required.

## Option A: open a ranking-update issue (no git needed)

1. Open https://www.hltv.org/ranking/1
2. Copy the current Top 30 as plain lines (`1 Vitality`, `2 Spirit`, ...).
3. Open a **ranking-update** issue (template:
   `.github/ISSUE_TEMPLATE/ranking-update.yml`), paste the ranking, the date,
   and the source URL.
4. A maintainer will import and review it.

## Option B: run the importer and open a PR

```bash
pip install -e ".[dev]"

python -m cs2_pro_settings ranking import-hltv \
  --date 2026-08-10 \
  --source-url https://www.hltv.org/ranking/1/2026/august/10 \
  --stdin < top30.txt
```

Validation enforced by the importer:

- exactly ranks 1–30, unique ranks, unique teams, continuous numbering;
- `--source-url` and `--date` required;
- every team must resolve in `config/team-mappings.yaml` — unresolved teams
  fail the import (`UNRESOLVED`); add a mapping if the team is missing.

Then:

```bash
python -m pytest
git checkout -b rankings/YYYY-MM-DD
git add config/rankings/hltv/ config/team-mappings.yaml
git commit -m "data: import HLTV ranking snapshot YYYY-MM-DD"
git push origin rankings/YYYY-MM-DD
```

Open a PR. A maintainer reviews, then activates the snapshot by updating
`config/cohort.yaml` (`cohort.core`) via `activate_snapshot` — activation is
a human decision, not automated.

## Watchlist nominations

Use the **watchlist** issue template to nominate a team
(near_top30 / rising_team / regional_interest / notable_team). Issues only
nominate; they never auto-modify config.

## What NOT to do

- Do not scrape HLTV (anti-bot / policy). Rankings are manual.
- Do not add anti-bot bypass, proxies, CAPTCHA solving, or browser
  automation.
- Do not change historical 2026-05 numbers or `reports/2026-05.md`.
- Do not commit raw row-level source data or raw HTML.
- Do not merge automation PRs without human review of conclusions.
