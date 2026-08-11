# Ranking snapshots (manual, versioned)

This directory holds **manually imported, versioned HLTV World Ranking Top
30 snapshots**, one file per ranking date: `YYYY-MM-DD.yaml`.

HLTV itself is **never scraped**; each snapshot is pasted by a maintainer or
contributor from the published ranking page
(`https://www.hltv.org/ranking/teams/YYYY/month/DD`), validated with
`python -m cs2_pro_settings ranking import-hltv`, reviewed, and activated
as `cohort.reference` (HLTV is a REFERENCE ranking — the PRIMARY Core is the
Valve Global Ranking, see `../valve/`).

A snapshot contains: provider, ranking_authority, ranking_type, date,
source_url, source_host, top_n, and the ordered `teams` list (rank,
display_name, team_id, settings_slug). Player names on the ranking page are
not imported and are not current roster truth.
