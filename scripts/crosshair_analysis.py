"""Offline crosshair quality/export and exploratory analysis.

Row-level inputs stay in work/. Public inputs are anonymous counts of three
geometry parameters, never identities, share codes or player-level settings.
Run: python scripts/crosshair_analysis.py --work work --output data/aggregate/analysis/2026-10-08-crosshair.json
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import re

import numpy as np
import pandas as pd

PIXEL_FORMATS = {"cs2-v1", "legacy-v3", "legacy-v4"}
GEOMETRY = ("crosshair_size", "crosshair_gap", "crosshair_thickness")


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def counted(values):
    counts = Counter(values)
    return {"valid_n": sum(counts.values()), "categories": dict(sorted(counts.items()))}


def complete_geometry(row):
    return all(isinstance(row.get(k), (int, float)) and not isinstance(row.get(k), bool)
               and math.isfinite(row[k]) for k in GEOMETRY)


def verified_date(row):
    return ((row.get("provenance") or {}).get("crosshair_style") or {}).get("source_updated_at")


def export_review(work: Path):
    metrics = json.loads((work / "metrics.json").read_text())
    normalized = json.loads((work / "current-normalized.json").read_text())
    manifest = json.loads((work / "collection-manifest.json").read_text())
    ids = metrics["panel"]["player_ids"]
    assert len(ids) == len(set(ids)), "duplicate Core identities"
    assert all(pid in normalized for pid in ids), "panel/normalized join loss"
    core = [normalized[pid] for pid in ids]
    snapshot_date = metrics["aggregate"]["snapshot_date"]
    rows = [p for p in core if p.get("crosshair_style") is not None]
    native = [p for p in rows if p.get("crosshair_format") == "cs2-v1"]
    fresh = [p for p in native if verified_date(p) and "2026-10-01" <= verified_date(p) <= snapshot_date]
    # Shape-specific, current-format, same-reference-height primary analysis.
    static = [p for p in fresh if p.get("crosshair_style") == "4" and complete_geometry(p)
              and isinstance(p.get("crosshair_screen_height"), int) and p["crosshair_screen_height"] >= 240]
    heights = Counter(p["crosshair_screen_height"] for p in static)
    height = sorted(heights, key=lambda h: (-heights[h], h))[0] if heights else None
    primary = [p for p in static if p["crosshair_screen_height"] == height]
    sensitivity = [p for p in native if p.get("crosshair_style") == "4"
                   and p.get("crosshair_screen_height") == height and complete_geometry(p)]
    def joint(group):
        counts = Counter(tuple(p[k] for k in GEOMETRY) for p in group)
        return {"valid_n": len(group), "combinations": [
            {"length": key[0], "gap_offset": key[1], "thickness": key[2], "count": count}
            for key, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]}
    invalid = Counter()
    for p in rows:
        pixel = p.get("crosshair_format") in PIXEL_FORMATS
        for key in GEOMETRY:
            v = p.get(key)
            if v is not None and (not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v)):
                invalid[key] += 1
        if pixel:
            for key, lo, hi in [("crosshair_size", 0, 255), ("crosshair_gap", -3840, 3840),
                                ("crosshair_thickness", 0, 32), ("crosshair_screen_height", 240, 65535),
                                ("crosshair_alpha", 0, 255), ("crosshair_outline_mode", 0, 2)]:
                v = p.get(key)
                if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float))
                                      or not math.isfinite(v) or not lo <= v <= hi or not float(v).is_integer()):
                    invalid[key] += 1
            for c in "rgb":
                v = p.get(f"crosshair_color_{c}")
                if v is not None and (isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= 255):
                    invalid[f"crosshair_color_{c}"] += 1
    fields = ["crosshair_format", "crosshair_style", *GEOMETRY, "crosshair_screen_height",
              "crosshair_dot", "crosshair_outline_mode", "crosshair_t_style", "crosshair_alpha",
              "crosshair_color_r", "crosshair_color_g", "crosshair_color_b"]
    missing = {k: {"valid_n": sum(p.get(k) is not None for p in core),
                   "missing_n": sum(p.get(k) is None for p in core), "cohort_n": len(core)} for k in fields}
    dates = [verified_date(p) for p in rows]
    invalid_dates = sum(1 for d in dates if d and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d))
    team_coverage = []
    for team in sorted({p.get("team") for p in core}):
        members = [p for p in core if p.get("team") == team]
        known = sum(p.get("crosshair_style") is not None for p in members)
        team_coverage.append({"team": team, "cohort_n": len(members), "crosshair_valid_n": known,
                              "missing_n": len(members) - known})
    identities = json.loads((work / "identities.json").read_text())["players"]
    identity_map = {p["player_id"]: p for p in identities}
    roster_outliers = [t for t in team_coverage if t["cohort_n"] != 5]
    outlier_teams = {t["team"] for t in roster_outliers}
    quality = {
        "grain": "one current Core roster member; field values from CS2Settings",
        "identity_duplicate_n": len(ids) - len(set(ids)),
        "non_steam_identity_n": sum(not re.fullmatch(r"steam:\d{17}", pid) for pid in ids),
        "invalid_values": dict(invalid), "invalid_date_n": invalid_dates,
        "future_page_date_n": sum(bool(d and d > snapshot_date) for d in dates),
        "missing_page_date_n": sum(d is None for d in dates),
        "field_completeness": missing, "team_coverage": team_coverage,
        "page_verified_dates": counted([d for d in dates if d]),
        "native_format_before_system_update_n": sum(bool(verified_date(p) and verified_date(p) < "2026-09-23") for p in native),
        "primary_source_count": 1,
        "roster_size_outliers": roster_outliers,
        "missing_role_in_outlier_rosters_n": sum(p.get("team") in outlier_teams and not identity_map[p["player_id"]].get("role") for p in core),
        "team_membership_conflict_n": len(json.loads((work / "team-membership-conflicts.json").read_text())),
        "source_roster_ambiguity_n": len(json.loads((work / "roster-membership-ambiguities.json").read_text())),
        "notes": ["lastVerified is page verification, not crosshair observation time.",
                  "New share codes may be converted; they do not prove recent player choice.",
                  "Scope/outline colors and dynamic details are not extracted; independent match verification is absent.",
                  "HLTV reference remains 2026-08-03; this analysis uses only 2026-10-05 VRS Core."]}
    return {
        "schema_version": "crosshair-analysis-v1", "snapshot_date": snapshot_date,
        "ranking_date": metrics["aggregate"]["scope"]["core_snapshot"],
        "source": {"name": "cs2settings", "url": "https://cs2settings.com/players", "retrieved_at": snapshot_date},
        "collection": {k: manifest[k] for k in ["requested_core_teams", "successful_core_team_rosters", "expected_core_players", "successful_core_players", "collection_complete", "incomplete_reasons"]},
        "cohort_n": len(core), "crosshair_valid_n": len(rows), "native_format_n": len(native),
        "native_recent_page_n": len(fresh), "recent_static_height_counts": counted([str(p["crosshair_screen_height"]) for p in static]),
        "formats": counted([p["crosshair_format"] for p in rows]), "quality": quality,
        "new_format_choices": {k: counted([str(p[k]) for p in native if p.get(k) is not None])
                               for k in ["crosshair_style", "crosshair_dot", "crosshair_outline_mode", "crosshair_t_style", "crosshair_alpha"]},
        "geometry_sample": {"format": "cs2-v1", "style": "4", "reference_height": height,
                            "page_verified_from": "2026-10-01", "page_verified_through": snapshot_date,
                            "selection": "largest reference-height stratum among recent-page static crosses", **joint(primary)},
        "geometry_sensitivity_all_dates": joint(sensitivity),
        "input_metric_sha256": canonical_hash(metrics["aggregate"]),
    }


def expand_joint(block):
    # Reconstruct only anonymous three-parameter observations from counts.
    return np.repeat(np.array([[r["length"], r["gap_offset"], r["thickness"]]
                               for r in block["combinations"]], dtype=float),
                     [r["count"] for r in block["combinations"]], axis=0)


def distances(x, weights=None):
    spread = np.quantile(x, .75, axis=0) - np.quantile(x, .25, axis=0)
    spread = np.where(spread > 0, spread, np.ptp(x, axis=0))
    spread = np.where(spread > 0, spread, 1.)
    weights = np.array(weights if weights is not None else [1/3]*3)
    return (np.abs(x[:, None, :] - x[None, :, :]) / spread * weights).sum(axis=2), spread


def medoids(distance, k):
    """Deterministic greedy initialization + PAM swaps; ties use input order."""
    n = len(distance)
    chosen = [int(np.argmin(distance.sum(axis=1)))]
    while len(chosen) < k:
        candidates = [i for i in range(n) if i not in chosen]
        chosen.append(min(candidates, key=lambda i: (float(np.minimum(distance[:, chosen].min(axis=1), distance[:, i]).sum()), i)))
    for _ in range(40):
        current = float(distance[:, chosen].min(axis=1).sum())
        best = (current, chosen)
        for position in range(k):
            for candidate in range(n):
                if candidate in chosen:
                    continue
                trial = chosen.copy(); trial[position] = candidate
                score = float(distance[:, trial].min(axis=1).sum())
                if score < best[0] - 1e-9:
                    best = (score, trial)
        if best[0] >= current - 1e-9:
            break
        chosen = best[1]
    return chosen, distance[:, chosen].argmin(axis=1)


def silhouette(distance, labels):
    values = []
    for i in range(len(labels)):
        same = np.flatnonzero(labels == labels[i]); same = same[same != i]
        if not len(same): values.append(0.); continue
        a = distance[i, same].mean()
        b = min(distance[i, labels == label].mean() for label in set(labels) if label != labels[i])
        values.append((b-a)/max(a,b) if max(a,b) else 0.)
    return float(np.mean(values))


def adjusted_rand(a, b):
    table = Counter(zip(a.tolist(), b.tolist()))
    ca, cb = Counter(a.tolist()), Counter(b.tolist())
    pair = lambda n: n*(n-1)/2
    n_pairs = pair(len(a))
    observed = sum(pair(n) for n in table.values())
    expected = sum(pair(n) for n in ca.values()) * sum(pair(n) for n in cb.values()) / n_pairs
    maximum = (sum(pair(n) for n in ca.values()) + sum(pair(n) for n in cb.values()))/2
    return float((observed-expected)/(maximum-expected)) if maximum != expected else 1.


def analyze(review, bootstrap_runs=50):
    x = expand_joint(review["geometry_sample"])
    assert len(x) >= 10, "insufficient comparable sample"
    distance, scale = distances(x)
    candidates = []
    for k in range(2, min(6, len(np.unique(x, axis=0)))):
        centers, labels = medoids(distance, k)
        sizes = np.bincount(labels, minlength=k)
        candidates.append({"k": k, "silhouette": round(silhouette(distance, labels), 4),
                           "sizes": sizes.tolist(), "minimum_size_pass": bool(sizes.min() >= max(5, math.ceil(len(x)*.1)))})
    feasible = [c for c in candidates if c["minimum_size_pass"]]
    selected = max(feasible, key=lambda c: (c["silhouette"], -c["k"])) if feasible else None
    frame = pd.DataFrame(x, columns=["length", "gap_offset", "thickness"])
    results = {"sample_n": len(x), "unique_geometry_n": len(np.unique(x, axis=0)),
               "spearman": frame.rank().corr().round(4).to_dict(),
               "distance": "Manhattan, each feature divided by population IQR, equal weights; no RGB or decorators",
               "scale": scale.tolist(), "candidates": candidates, "selected": selected,
               "selection_rule": "best silhouette among k=2..5 with every group >=max(5,10% of sample); exploratory"}
    if selected:
        k = selected["k"]; centers, labels = medoids(distance, k)
        results["groups"] = [{"group": int(i+1), "count": int((labels==i).sum()),
                              "medoid": x[c].tolist(),
                              "median": np.median(x[labels==i], axis=0).tolist(),
                              "min": x[labels==i].min(axis=0).tolist(), "max": x[labels==i].max(axis=0).tolist()}
                             for i,c in enumerate(centers)]
        rng = np.random.default_rng(20261008); stability = []
        for _ in range(bootstrap_runs):
            indices = rng.integers(0, len(x), len(x))
            # Fix the original distance scale; perturb empirical weighting.
            sample_distance = distance[np.ix_(indices, indices)]
            sampled_centers, _ = medoids(sample_distance, k)
            predicted = distance[:, indices[sampled_centers]].argmin(axis=1)
            stability.append(adjusted_rand(labels, predicted))
        unique = np.unique(x, axis=0); ud, _ = distances(unique)
        _, ul = medoids(ud, k)
        wd,_ = distances(x, [.5,.25,.25]);_, wl = medoids(wd,k)
        results["sensitivity"] = {"bootstrap_runs":bootstrap_runs,"bootstrap_ari_median":round(float(np.median(stability)),4),
                                  "bootstrap_ari_p10":round(float(np.quantile(stability,.1)),4),
                                  "length_weighted_ari":round(adjusted_rand(labels,wl),4),
                                  "unique_template_silhouette":round(silhouette(ud,ul),4),
                                  "caveat":"Bootstrap resamples anonymous parameter tuples, not teams; it cannot test independent-source truth or team dependence."}
    other = expand_joint(review["geometry_sensitivity_all_dates"])
    results["all_date_sensitivity"] = {"sample_n":len(other),"spearman":pd.DataFrame(other,columns=frame.columns).rank().corr().round(4).to_dict()}
    results["caveats"] = ["Associations describe source records, not causation, aiming performance or proof of independent player choice.",
                           "Selected groups are exploratory partitions, not established natural style categories.",
                           "Dominant repeated templates may originate from conversion or copying; independent verification is required.",
                           "Only one format, one shape and one reference height are modeled; results do not represent all professionals."]
    return results


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work',type=Path,default=Path('work'))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    review=export_review(args.work);review['analysis']=analyze(review)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:review[k] for k in ['snapshot_date','ranking_date','cohort_n','crosshair_valid_n','native_format_n','native_recent_page_n']},ensure_ascii=False))
    print(json.dumps(review['analysis'],indent=2))


if __name__=='__main__':main()
