# Source audit: prosettings.net

- checked_at: 2026-08-10
- base URL: https://prosettings.net
- adapter role: compatibility / user-triggered local reconciliation
- scheduled_enabled: false

## Policy

- robots.txt: HTTP 200; blocks `/wp-json/`, `/?rest_route=`, `/wp-admin/`,
  `/wp-content/cache/`, `/wp-content/plugins/`, `/wp-login.php`,
  `/wp-includes/`, `/?s=` (internal search). Player and list pages are NOT
  blocked.
- The v1 (2026-05) snapshot was collected from this site. The v2 project does
  NOT default to mirroring third-party row-level data; this adapter exists for
  compatibility and user-triggered reconciliation only.

## Technical accessibility

- Normal GET of `/lists/cs2/` and `/players/<slug>/` returned HTTP 200 at the
  original collection time (2026-05) and remains the v1 scraper's path.
- No anti-bot bypass is used or implemented.

## Adapter

- `src/cs2_pro_settings/sources/prosettings.py` — minimal migration of the
  v1 notebook parsing logic (list table rows; detail page label/value pairs).

## Known limitations

- Detail-page parsing is coarser than the v2 primary source (no structured
  data blob); SteamID is not reliably available, so identity resolution falls
  back to `source:prosettings:<slug>`.
