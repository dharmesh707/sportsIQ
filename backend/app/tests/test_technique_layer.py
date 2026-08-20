"""
Tests for the transparent comparison baseline: similarity, level estimation,
pose quality, recommendation generation, and the degenerate-input handling
that keeps NaN/inf from silently poisoning a score.
"""

import math

import pytest

from app.services import sports_registry
from app.services.technique import comparison, quality, recommendations
from app.services.technique.config import (
    LEVEL_BANDS,
    VERDICT_GOOD,
    VERDICT_NEEDS_WORK,
    band_for,
)
from app.services.technique.reference_profiles import (
    ReferenceProfileError,
    any_validated,
    get_profile,
    load_profiles,
    profile_ids,
)

PERFECT = {
    "elbow_angle": 165.0,
    "shoulder_elevation": 78.0,
    "knee_angle": 160.0,
    "hip_shoulder_separation": 32.0,
    "torso_inclination": 12.0,
}


# --------------------------------------------------------------------------
# Reference profiles
# --------------------------------------------------------------------------


def test_profiles_load_and_are_not_claimed_as_validated():
    """
    The honesty gate. Nothing in this repo is measured athlete data, so
    nothing may report itself as validated. If this test ever fails, either
    real data was added (update the docs) or someone mislabelled a
    hand-typed number.
    """
    profiles = load_profiles()
    assert len(profiles) >= 2
    assert all(p.provenance == "hand_authored" for p in profiles)
    assert not any_validated()


def test_profile_lookup():
    assert "viktor_axelsen" in profile_ids()
    assert get_profile("viktor_axelsen").display_name == "Viktor Axelsen"
    with pytest.raises(KeyError):
        get_profile("nobody")


# --------------------------------------------------------------------------
# Comparison
# --------------------------------------------------------------------------


def test_exact_match_scores_one_hundred():
    result = comparison.compare(PERFECT)
    assert result is not None
    assert result.overall_similarity == pytest.approx(100.0, abs=0.1)
    assert result.closest.profile_id == "viktor_axelsen"
    assert all(f.verdict == VERDICT_GOOD for f in result.features)


def test_closest_profile_is_selected_not_the_default():
    """Feeding Momota's exact numbers must select Momota, not the default."""
    momota = dict(get_profile("kento_momota").features)
    result = comparison.compare(momota)
    assert result is not None
    assert result.closest.profile_id == "kento_momota"


def test_all_profiles_are_scored_and_sorted_descending():
    result = comparison.compare(PERFECT)
    assert result is not None
    sims = [m.similarity for m in result.all_matches]
    assert len(sims) == len(load_profiles())
    assert sims == sorted(sims, reverse=True)


def test_one_bad_feature_cannot_zero_the_whole_score():
    """
    The v1 formula (100 - mean_abs_diff * 2) floored at 0 once the mean error
    hit 50 deg, so a single badly-measured feature destroyed the result.
    """
    features = dict(PERFECT)
    features["hip_shoulder_separation"] = 90.0  # maximally wrong
    result = comparison.compare(features)
    assert result is not None
    assert result.overall_similarity > 60.0


def test_nan_and_inf_features_are_excluded_not_scored_as_zero():
    features = dict(PERFECT)
    features["elbow_angle"] = float("nan")
    features["knee_angle"] = float("inf")
    result = comparison.compare(features)
    assert result is not None
    keys = {f.key for f in result.features}
    assert "elbow_angle" not in keys
    assert "knee_angle" not in keys
    # Remaining features still matched exactly, so similarity stays high.
    assert result.overall_similarity == pytest.approx(100.0, abs=0.1)


def test_all_features_unusable_returns_none():
    """
    Distinguishes "we measured nothing" from "technique is 0% similar".
    Reporting the latter for the former would be a lie the UI would repeat.
    """
    assert comparison.compare({}) is None
    assert comparison.compare({"elbow_angle": float("nan")}) is None


def test_missing_feature_is_skipped_without_error():
    result = comparison.compare({"elbow_angle": 165.0})
    assert result is not None
    assert [f.key for f in result.features] == ["elbow_angle"]


def test_deviation_sign_is_preserved():
    result = comparison.compare({**PERFECT, "elbow_angle": 145.0})
    assert result is not None
    elbow = next(f for f in result.features if f.key == "elbow_angle")
    assert elbow.deviation == pytest.approx(-20.0, abs=0.1)
    assert elbow.abs_deviation == pytest.approx(20.0, abs=0.1)


def test_comparison_basis_never_claims_validation():
    result = comparison.compare(PERFECT)
    assert result is not None
    basis = result.comparison_basis.lower()
    assert "reference profile" in basis
    assert "as good as" not in basis
    assert "validated" not in basis


# --------------------------------------------------------------------------
# Level estimation
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (100.0, "ELITE_REFERENCE_LIKE"),
        (90.0, "ELITE_REFERENCE_LIKE"),
        (89.9, "ADVANCED"),
        (75.0, "ADVANCED"),
        (74.9, "INTERMEDIATE"),
        (60.0, "INTERMEDIATE"),
        (59.9, "DEVELOPING"),
        (40.0, "DEVELOPING"),
        (39.9, "BEGINNER"),
        (0.0, "BEGINNER"),
    ],
)
def test_level_band_edges(score, expected):
    assert band_for(score, LEVEL_BANDS, default="BEGINNER") == expected


# --------------------------------------------------------------------------
# Pose quality
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("detected", "total", "band", "reliable"),
    [
        (100, 100, "HIGH", True),
        (80, 100, "HIGH", True),
        (79, 100, "MEDIUM", True),
        (50, 100, "MEDIUM", True),
        (49, 100, "LOW", False),
        (30, 100, "LOW", False),
        (29, 100, "REJECT", False),
        (0, 100, "REJECT", False),
    ],
)
def test_pose_quality_bands(detected, total, band, reliable):
    q = quality.assess(detected, total)
    assert q.band == band
    assert q.is_reliable is reliable


def test_pose_quality_handles_zero_frames_without_dividing_by_zero():
    q = quality.assess(0, 0)
    assert q.band == "REJECT"
    assert q.detection_rate == 0.0
    assert not math.isnan(q.detection_rate)


def test_pose_quality_rate_is_clamped():
    q = quality.assess(150, 100)  # nonsensical input must not exceed 1.0
    assert q.detection_rate <= 1.0


# --------------------------------------------------------------------------
# Recommendations
# --------------------------------------------------------------------------


def test_recommendations_are_deterministic():
    features = {**PERFECT, "elbow_angle": 110.0}
    result = comparison.compare(features)
    first, _ = recommendations.build(result, reliable=True)
    second, _ = recommendations.build(result, reliable=True)
    assert [r.text for r in first] == [r.text for r in second]


def test_recommendation_direction_matches_deviation_sign():
    """Under-extension and over-extension must not get the same advice."""
    under = comparison.compare({**PERFECT, "elbow_angle": 110.0})
    over = comparison.compare({**PERFECT, "elbow_angle": 179.0})
    under_recs, _ = recommendations.build(under, reliable=True)
    over_recs, _ = recommendations.build(over, reliable=True)
    under_text = next(r.text for r in under_recs if r.feature_key == "elbow_angle")
    assert "more extended elbow" in under_text
    over_elbow = [r for r in over_recs if r.feature_key == "elbow_angle"]
    if over_elbow:
        assert "more extended elbow" not in over_elbow[0].text


def test_every_recommendation_traces_to_a_measured_deviation():
    result = comparison.compare({**PERFECT, "knee_angle": 90.0})
    recs, _ = recommendations.build(result, reliable=True)
    knee = [r for r in recs if r.feature_key == "knee_angle"]
    assert knee
    assert knee[0].measured_deviation > 0


def test_unreliable_pose_suppresses_technical_coaching():
    """
    Confident joint-angle corrections from a poorly tracked clip are the most
    harmful output this system could produce.
    """
    result = comparison.compare({**PERFECT, "knee_angle": 90.0})
    recs, strengths = recommendations.build(result, reliable=False)
    assert len(recs) == 1
    assert recs[0].feature_key == "pose_quality"
    assert strengths == []


def test_good_form_still_returns_a_recommendation():
    result = comparison.compare(PERFECT)
    recs, _ = recommendations.build(result, reliable=True)
    assert len(recs) >= 1


def test_faults_are_generated_from_verdicts():
    result = comparison.compare({**PERFECT, "knee_angle": 90.0})
    faults = recommendations.to_fault_dicts(result, contact_frame=42)
    assert faults
    assert all(f["frame"] == 42 for f in faults)
    hard = [f for f in faults if f["type"] == "hard"]
    assert any(f["fault_code"] == "knee_angle_deviation" for f in hard)


def test_perfect_form_generates_no_faults():
    result = comparison.compare(PERFECT)
    assert recommendations.to_fault_dicts(result, contact_frame=1) == []


# --------------------------------------------------------------------------
# Sports registry
# --------------------------------------------------------------------------


def test_only_badminton_is_marked_supported():
    supported = [s for s in sports_registry.all_sports() if s.status == "SUPPORTED"]
    assert [s.sport_type.value for s in supported] == ["badminton"]


def test_preview_sports_are_labelled_simulated():
    for sport in sports_registry.all_sports():
        if sport.status == "PREVIEW":
            assert sport.data_source == "simulated"
