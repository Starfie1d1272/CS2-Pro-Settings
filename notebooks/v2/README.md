# v2 analysis notebooks

`2026-10-08-crosshair.ipynb` checks the October candidate's source coverage,
field completeness, page dates, format migration, anonymous geometry
combinations, popular observed appearance templates, color choices and exploratory medoid groups. It consumes committed aggregate
counts only and can be executed without network access or private player data.
It does not render game-accurate crosshairs or establish match usage.

From the repository root, use the project environment plus notebook tooling:

```bash
pip install -e ".[dev]"
pip install nbformat nbclient ipykernel nbconvert
python -m jupyter nbconvert --execute --to notebook --inplace notebooks/v2/2026-10-08-crosshair.ipynb
```

The saved notebook includes tables and figures. It checks that the analysis
input matches the frozen candidate aggregate, and that recomputation reproduces
the stored analytical results. Generated analytical figures are in
`figures/analysis/2026-10-08/`.

Regenerating the public analysis input from a local collection is separate:

```bash
python scripts/crosshair_analysis.py --work work --output data/aggregate/analysis/2026-10-08-crosshair.json
```

`work/` stays private and gitignored. Public inputs contain anonymous counts of
geometric and repeated appearance combinations, exact RGB counts, source/quality summaries and cohort metadata; no
SteamIDs, player records, share codes or identity lists are distributed.
The dated snapshot is a review candidate; `latest.json` remains accepted history.

Validation for this candidate: all cells were executed with nbclient, and the
exported charts were visually inspected. An HTML preview was generated, but
headless Chromium timed out before producing a whole-notebook screenshot;
whole-page browser layout has not been verified.
