"""
Single source of truth for every threshold the technique layer uses.

Nothing in this package (and nothing in the frontend) should hard-code a
number that lives here. Bands are ordered high-to-low and evaluated with
`>=`, so changing a band edge in one place changes it everywhere.

IMPORTANT HONESTY NOTE
----------------------
Every band below is a PRODUCT HEURISTIC. None of it is derived from a
validated dataset of labelled player skill levels, because this repository
does not contain one. They exist so the UI can say something more useful
than a bare number - not because 74.9 and 75.0 are a meaningful boundary in
badminton biomechanics. Anything surfaced from these values must be labelled
"estimated", never "measured" and never "certified".
"""

from __future__ import annotations

from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# Pose quality
# --------------------------------------------------------------------------
# Applied to the detector's real `detection_rate` (detected frames / total
# frames). REJECT_BELOW matches the detector's own existing hard cutoff of
# 0.30 - that threshold already existed in
# scripts/analyze_badminton_video_rule_based.py and is preserved, not changed.

POSE_QUALITY_BANDS: tuple[tuple[float, str], ...] = (
    (0.80, "HIGH"),
    (0.50, "MEDIUM"),
    (0.30, "LOW"),
)
POSE_QUALITY_REJECT_BELOW: float = 0.30

# Minimum absolute number of pose-detected frames, independent of rate.
# Also pre-existing detector behaviour, lifted here so it is configurable.
MIN_DETECTED_FRAMES: int = 5

# Below this quality we still return a result, but flag it as unreliable and
# suppress the confident framing in the UI.
QUALITY_CAVEAT_BELOW: float = 0.50

POSE_QUALITY_MESSAGES: dict[str, str] = {
    "HIGH": "The athlete was tracked consistently through the clip.",
    "MEDIUM": (
        "The athlete was tracked for most of the clip. Angle measurements are "
        "usable but slightly less precise than a clean recording."
    ),
    "LOW": (
        "Results may be less reliable because the athlete was not detected "
        "consistently. Re-record with the full body in frame and better lighting."
    ),
}

# --------------------------------------------------------------------------
# Estimated technique level
# --------------------------------------------------------------------------
# Applied to the overall similarity score (0-100) against the closest
# reference profile. Heuristic - see the honesty note at the top of the file.

LEVEL_BANDS: tuple[tuple[float, str], ...] = (
    (90.0, "ELITE_REFERENCE_LIKE"),
    (75.0, "ADVANCED"),
    (60.0, "INTERMEDIATE"),
    (40.0, "DEVELOPING"),
    (0.0, "BEGINNER"),
)

LEVEL_DESCRIPTIONS: dict[str, str] = {
    "ELITE_REFERENCE_LIKE": (
        "Your measured joint angles at contact sit very close to the reference "
        "profile across every tracked feature."
    ),
    "ADVANCED": "Most tracked features are close to the reference profile.",
    "INTERMEDIATE": "Several features match the reference profile; a few differ noticeably.",
    "DEVELOPING": "Some features are on track, but most differ from the reference profile.",
    "BEGINNER": "Most tracked features differ substantially from the reference profile.",
}

# --------------------------------------------------------------------------
# Per-feature comparison
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class FeatureSpec:
    """
    How one pose-derived feature is compared against a reference profile.

    tolerance_deg
        The deviation at which per-feature similarity reaches 0. Chosen from
        the plausible range of variation for that joint, not fitted to data.
    good_deg / slight_deg
        Verdict boundaries. <= good_deg -> GOOD, <= slight_deg ->
        SLIGHT_DIFFERENCE, otherwise NEEDS_IMPROVEMENT.
    weight
        Contribution to the overall similarity score. Elbow and knee carry
        more weight because they are true interior joint angles and are the
        most stable to measure from a single 2D camera. Rotation-style
        features are noisier and weighted down accordingly.
    """

    key: str
    label: str
    unit: str = "deg"
    tolerance_deg: float = 45.0
    good_deg: float = 8.0
    slight_deg: float = 20.0
    weight: float = 1.0
    higher_is: str = "neutral"  # "neutral" | "more" | "less" - drives phrasing only


FEATURE_SPECS: tuple[FeatureSpec, ...] = (
    FeatureSpec(
        key="elbow_angle",
        label="Elbow angle",
        tolerance_deg=50.0,
        good_deg=8.0,
        slight_deg=20.0,
        weight=1.3,
    ),
    FeatureSpec(
        key="shoulder_elevation",
        label="Shoulder elevation",
        tolerance_deg=45.0,
        good_deg=8.0,
        slight_deg=18.0,
        weight=1.2,
    ),
    FeatureSpec(
        key="knee_angle",
        label="Knee angle",
        tolerance_deg=50.0,
        good_deg=10.0,
        slight_deg=22.0,
        weight=1.0,
    ),
    FeatureSpec(
        key="hip_shoulder_separation",
        label="Hip-shoulder separation",
        tolerance_deg=40.0,
        good_deg=10.0,
        slight_deg=20.0,
        weight=0.7,  # 2D proxy for trunk rotation - noisiest feature, weighted down
    ),
    FeatureSpec(
        key="torso_inclination",
        label="Torso inclination",
        tolerance_deg=35.0,
        good_deg=7.0,
        slight_deg=15.0,
        weight=0.8,
    ),
)

FEATURE_SPEC_BY_KEY: dict[str, FeatureSpec] = {spec.key: spec for spec in FEATURE_SPECS}

VERDICT_GOOD = "GOOD"
VERDICT_SLIGHT = "SLIGHT_DIFFERENCE"
VERDICT_NEEDS_WORK = "NEEDS_IMPROVEMENT"

# A feature only becomes a "strength" or a "weakness" at these similarity
# levels, so borderline features are reported neutrally instead of being
# spun either way.
STRENGTH_SIMILARITY_MIN: float = 85.0
WEAKNESS_SIMILARITY_MAX: float = 60.0
MAX_RECOMMENDATIONS: int = 4

# --------------------------------------------------------------------------
# Video guardrails
# --------------------------------------------------------------------------

MIN_VIDEO_FRAMES: int = 10
MAX_VIDEO_FRAMES: int = 3000  # ~100s at 30fps; keeps CPU inference bounded
MAX_VIDEO_SECONDS: float = 120.0
MIN_VIDEO_DIMENSION: int = 120  # px on the short side


def band_for(value: float, bands: tuple[tuple[float, str], ...], default: str) -> str:
    """Return the first band label whose threshold `value` meets or exceeds."""
    for threshold, label in bands:
        if value >= threshold:
            return label
    return default
