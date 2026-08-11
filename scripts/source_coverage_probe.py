#!/usr/bin/env python3
"""Local targeted source-coverage probe for the six unresolved Core teams.

RUN MANUALLY (never in CI):
    python -m cs2_pro_settings probe-coverage

Probes candidate player pages ONLY (names come from the user-provided VRS
snapshot roster context — they are COVERAGE SEEDS, never current-roster
truth). No raw HTML is saved; results are structured into
work/source-coverage-audit.json (gitignored).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

WORK = ROOT / "work"

TEAMS = {
    "aurora": ["xantares", "woxic", "jimpphat", "kyxsan", "wicadia"],
    "big": ["tabsen", "jdc", "faven", "blamef", "gr1ks"],
    "inner-circle": ["cptkurtka023", "headtr1ck", "zerrofix", "onic", "dawy"],
    "magic": ["masvai", "sfade8", "aw", "moon", "tenzy"],
    "dendele": ["gafolo", "koala", "maxxkor", "rdnzao", "doc"],
    "hotu": ["n0rb3r7", "kade0", "mizu", "dwushka", "frontales"],
}

SOURCES = {
    "cs2settings": "https://cs2settings.com/players/{name}",
    "prosettings": "https://prosettings.net/players/{name}/",
    "proconfig": "https://proconfig.net/cs2/{name}/",
}

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def probe(url: str, timeout: int = 20) -> dict:
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": UA})
    except requests.RequestException as exc:
        return {"http": "error", "detail": str(exc)[:120]}
    if r.status_code != 200:
        return {"http": r.status_code}
    text = r.text
    steam = sorted(set(re.findall(r"steamcommunity\.com/profiles/(\d{15,17})", text)))
    has_vanity = bool(re.search(r"steamcommunity\.com/id/", text))
    team_hint = None
    m = re.search(r"team(?:name|id)?[\"':\s=]+([A-Za-z0-9 _.-]{2,30})", text[:200000], re.I)
    if m:
        team_hint = m.group(1)[:30]
    return {
        "http": 200,
        "steam_id": steam[0] if steam else None,
        "vanity_only": has_vanity and not steam,
        "team_hint": team_hint,
        "field_count_estimate": len(re.findall(r"<h[23]|<dt|<th", text)),
        "bytes": len(text),
    }


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    audit: dict = {"teams": {}}
    for team, names in TEAMS.items():
        team_entry: dict = {"players": {}}
        for name in names:
            player_entry: dict = {}
            for source, url_tpl in SOURCES.items():
                url = url_tpl.format(name=name)
                try:
                    player_entry[source] = probe(url)
                except Exception as exc:  # noqa: BLE001
                    player_entry[source] = {"http": "error", "detail": str(exc)[:120]}
            team_entry["players"][name] = player_entry
        audit["teams"][team] = team_entry
    out = WORK / "source-coverage-audit.json"
    out.write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
    # summary
    for team, t in audit["teams"].items():
        ok_cs = sum(1 for p in t["players"].values() if p.get("cs2settings", {}).get("http") == 200)
        ok_ps = sum(1 for p in t["players"].values() if p.get("prosettings", {}).get("http") == 200)
        ok_pc = sum(1 for p in t["players"].values() if p.get("proconfig", {}).get("http") == 200)
        steam_cs = sum(1 for p in t["players"].values()
                       if p.get("cs2settings", {}).get("steam_id"))
        steam_ps = sum(1 for p in t["players"].values()
                       if p.get("prosettings", {}).get("steam_id"))
        print(f"{team}: cs2settings {ok_cs}/5 (steam {steam_cs}/5) | "
              f"prosettings {ok_ps}/5 (steam {steam_ps}/5) | proconfig {ok_pc}/5")
    print(f"audit written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
