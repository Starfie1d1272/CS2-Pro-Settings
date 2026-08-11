# Source audit: proconfig.net

- checked_at: 2026-08-10
- base URL: https://proconfig.net
- adapter role: secondary editorial cross-check (reconciliation / QC only)
- scheduled_enabled: false

## Domain correction

An earlier probe of `proconfig.gg` was **incorrect and is superseded**:
`proconfig.gg` is not registered (whois NOT FOUND; DNS sinkholed). The
correct target is `proconfig.net`, which resolves and serves normally.

## Policy

- robots.txt: HTTP 200; `User-agent: *` `Allow: /` with
  `Disallow: /downloads/ /product/ /search-index.json`. Player/list pages are
  allowed.
- terms/legal: an **editorial-process page** exists
  (`/editorial-process/`, last updated May 2026) documenting a "Verified
  Config & Gear" standard: fields are sourced from primary/reputable
  secondary evidence, cross-referenced where possible, and dated; fields that
  cannot meet the bar are left blank rather than guessed.

## Technical accessibility

- Normal GET returns HTTP 200 for `/`, `/cs2/`, `/editorial-process/`, and
  `/cs2/<slug>/` player pages; no CAPTCHA / bot challenge observed.
- Player pages expose semantic `<dt>/<dd>` label-value pairs plus JSON-LD
  (Person / ProfilePage.lastReviewed / FAQPage).

## Adapter

- `src/cs2_pro_settings/sources/proconfig.py` — fetch_player() only; no
  full-site enumeration; never defines the cohort; never replaces the primary
  source.
- Configured **disabled** (`config/sources.yaml`): enabled only after the
  user explicitly opts into reconciliation use.

## Known limitations

- Crosshair Color is rendered as RGB values; only a "Custom" category is
  derivable (no named preset detection).
- No Dot field on player pages.
- Crosshair style normalization differs from cs2settings (name vs numeric
  code); conflicts are surfaced by reconcile.py, never silently overwritten.
