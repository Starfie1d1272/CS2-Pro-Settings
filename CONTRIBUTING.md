# Contributing

Thanks for helping keep professional CS2 settings tracking alive. The
**most valuable contribution you can make is a fresh ranking snapshot** —
no scraper, no code required.

## Rankings (manual Top 30)

Two rankings are tracked; contributors may update either one:

- **Primary Core:** Valve Global Ranking (VRS) Top 30 →
  `config/rankings/valve/YYYY-MM-DD.yaml` (ranking authority: Valve;
  display page hosted by HLTV)
- **Reference:** HLTV World Ranking Top 30 →
  `config/rankings/hltv/YYYY-MM-DD.yaml` (ranking authority: HLTV)

## Option A: open a ranking-update issue (no git needed)

1. Open the ranking page (VRS:
   `https://www.hltv.org/valve-ranking/teams/YYYY/month/DD`; HLTV:
   `https://www.hltv.org/ranking/teams/YYYY/month/DD`).
2. Copy the current Top 30 as plain lines (`1 Spirit`, `2 Falcons`, ...).
3. Open a **ranking-update** issue (template:
   `.github/ISSUE_TEMPLATE/ranking-update.yml`), choose the provider
   (Valve VRS or HLTV), paste the ranking, the date, and the source URL.
4. A maintainer will import and review it.

## Option B: run the importer and open a PR

```bash
pip install -e ".[dev]"

# Valve Global Ranking (VRS) — primary Core
python -m cs2_pro_settings ranking import-vrs \
  --date 2026-08-10 \
  --source-url https://www.hltv.org/valve-ranking/teams/2026/august/10 \
  --stdin < top30.txt

# HLTV World Ranking — reference
python -m cs2_pro_settings ranking import-hltv \
  --date 2026-08-03 \
  --source-url https://www.hltv.org/ranking/teams/2026/august/3 \
  --stdin < top30.txt
```

Validation enforced by the importer (shared by both providers):

- exactly ranks 1–30, unique ranks, unique teams, continuous numbering;
- `--source-url` and `--date` required;
- every team must resolve in `config/team-mappings.yaml` — unresolved teams
  fail the import (`UNRESOLVED`); add a mapping if the team is missing.

Then:

```bash
python -m pytest
git checkout -b rankings/YYYY-MM-DD
git add config/rankings/ config/team-mappings.yaml
git commit -m "data: import ranking snapshot YYYY-MM-DD"
git push origin rankings/YYYY-MM-DD
```

Open a PR. A maintainer reviews, then activates the snapshot via
`activate_snapshot(target="core"|"reference")` — activation is a human
decision, not automated. A VRS snapshot can only activate as Core; an HLTV
snapshot only as reference.

**Ranking page player names are NOT current roster truth.** Do not submit
player rosters; the pipeline derives rosters independently from the
settings/roster source.

## Watchlist nominations

Use the **watchlist** issue template to nominate a team
(near_ranked_union / rising_team / regional_interest / notable_team).
Issues only nominate; they never auto-modify config.

## What NOT to do

- Do not scrape HLTV or any ranking page (anti-bot / policy). Rankings are
  manual.
- Do not add anti-bot bypass, proxies, CAPTCHA solving, or browser
  automation.
- Do not change historical 2026-05 numbers or `reports/2026-05.md`.
- Do not commit raw row-level source data or raw HTML.
