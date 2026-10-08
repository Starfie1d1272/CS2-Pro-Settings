"""Independent checks for exploratory medoids and public aggregate shaping."""
import importlib.util
from itertools import combinations
from pathlib import Path

import numpy as np

spec = importlib.util.spec_from_file_location('crosshair_analysis', Path(__file__).parents[1] / 'scripts/crosshair_analysis.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_pam_cost_matches_brute_force_on_separated_groups():
    points = np.array([[0,0,0],[1,0,0],[2,0,0],[10,0,0],[11,0,0],[12,0,0]], dtype=float)
    distance, _ = module.distances(points)
    centers, labels = module.medoids(distance,2)
    optimum = min(distance[:,list(pair)].min(axis=1).sum() for pair in combinations(range(6),2))
    assert np.isclose(distance[:,centers].min(axis=1).sum(), optimum)
    assert len(set(labels[:3])) == len(set(labels[3:])) == 1
    assert labels[0] != labels[-1]


def test_iqr_distance_invariant_to_common_linear_unit_change():
    points = np.array([[2,1,2],[4,2,1],[3,0,2],[8,3,1]],dtype=float)
    d,_ = module.distances(points)
    converted,_ = module.distances(points * np.array([2,2,2]))
    np.testing.assert_allclose(d,converted)
    assert np.allclose(np.diag(d),0)
    np.testing.assert_allclose(d,d.T)


def test_ari_ignores_label_names_and_detects_disagreement():
    assert module.adjusted_rand(np.array([0,0,1,1]),np.array([9,9,3,3])) == 1
    assert module.adjusted_rand(np.array([0,0,1,1]),np.array([0,1,0,1])) < 0


def test_joint_expansion_preserves_counts_without_identity_fields():
    joint={'combinations':[{'length':2,'gap_offset':1,'thickness':2,'count':3},
                           {'length':4,'gap_offset':2,'thickness':1,'count':2}]}
    expanded=module.expand_joint(joint)
    assert expanded.shape==(5,3)
    np.testing.assert_array_equal(expanded[:3],np.tile([2,1,2],(3,1)))


def test_recommendation_uses_observed_joint_choices_and_excludes_color():
    # Marginal majority values would create (2, 1, 1), absent from these rows.
    def row(length, gap, thickness, color):
        return dict(zip(module.APPEARANCE, (length, gap, thickness, False, 0, False, 255)),
                    crosshair_color_r=color)
    rows = ([row(2, 1, 2, i) for i in range(4)]
            + [row(2, 0, 1, i) for i in range(3)]
            + [row(4, 1, 1, i) for i in range(3)] + [{"crosshair_size": 2}])
    result = module.appearance_counts(rows)
    assert result["valid_n"] == 10 and result["missing_n"] == 1
    top = result["combinations"][0]
    assert tuple(top[k] for k in module.GEOMETRY) == (2, 1, 2)
    assert top["count"] == 4
    assert all(tuple(r[k] for k in module.GEOMETRY) != (2, 1, 1)
               for r in result["combinations"])


def test_common_scale_accepts_different_heights_and_groups_proportional_choices():
    def row(height, length, gap, thickness):
        return dict(zip(module.APPEARANCE, (length, gap, thickness, False, 0, False, 255)),
                    crosshair_format="cs2-v1", crosshair_screen_height=height)
    a = row(720, 2, 1, 2)
    b = row(1440, 4, 2, 4)
    c = row(1080, 2, 1, 2)
    normalized = [module.normalize_geometry(r) for r in [a, b, c]]
    assert normalized[0]["crosshair_size"] == normalized[1]["crosshair_size"] == 3
    assert normalized[2]["crosshair_size"] == 2
    counted = module.appearance_counts(normalized)
    assert counted["valid_n"] == 3 and counted["combinations"][0]["count"] == 2
    other_target = module.appearance_counts([module.normalize_geometry(r, 960) for r in [a, b, c]])
    assert other_target["combinations"][0]["count"] == 2 and other_target["singleton_n"] == 1
    assert a["crosshair_size"] == 2  # source rows are untouched
    assert module.normalize_geometry(row(True, 2, 1, 2)) is None
    assert module.normalize_geometry({**a, "crosshair_format": "legacy-v1"}) is None


def test_normalization_does_not_merge_by_rounded_display_labels():
    a = dict(zip(module.APPEARANCE, (2, 1, 2, False, 0, False, 255)),
             crosshair_format="cs2-v1", crosshair_screen_height=960)
    b = {**a, "crosshair_screen_height": 961}
    result = module.appearance_counts([module.normalize_geometry(a), module.normalize_geometry(b)])
    assert result["valid_n"] == 2 and result["singleton_n"] == 2
    assert not result["combinations"]
