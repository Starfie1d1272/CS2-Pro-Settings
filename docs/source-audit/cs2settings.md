# Source audit: cs2settings.com

- checked_at: 2026-08-10
- base URL: https://cs2settings.com
- adapter role: v2 primary active source (roster + settings)
- scheduled_enabled: true

## Policy

- robots.txt: HTTP 200. `User-agent: *` → `Allow: /`; only AI crawlers
  (GPTBot, meta-externalagent) are Disallowed. Cloudflare-managed content
  signals: `search=yes, ai-train=no, use=reference`. Content signals address
  AI training/search use; they do not restrict the low-frequency, non-AI
  collection this project performs. This does NOT constitute a grant of
  rights over the data — see DATA_PROVENANCE.md.
- terms/legal: no dedicated terms/privacy page found in site navigation
  (`/about`, `/blog`, `/teams`, `/players`, `/tools/*`). The absence of a
  terms page is recorded as an unknown, NOT as permission.
- editorial/verification: player pages carry `lastVerified` dates.

## Technical accessibility

- Normal GET (desktop UA, no cookies) returns HTTP 200 for `/`, `/players`,
  `/teams/<slug>`, `/players/<slug>`; no CAPTCHA / bot challenge observed.
- Player data is embedded as a SvelteKit data blob in a `<script>` body;
  parsing is script-scoped and string/comment-aware (no CSS-class anchors).

## Adapter

- `src/cs2_pro_settings/sources/cs2settings.py`
- list_team_roster(): semantic role-anchor parsing of team pages.
- fetch_player(): structured blob -> ParsedPlayer (SteamID, team, role,
  country, lastVerified, mouse/crosshair/video/viewmodel/radar fields).
- Fail closed: any HTTP/parse failure raises SourceError.

## Known limitations

- Team slug set (37) does not cover all 41 legacy 2026-05 teams; unmapped
  legacy teams are recorded in config/cohort.yaml and cannot contribute an
  automatic roster.
- `lastVerified` freshness varies per player.
