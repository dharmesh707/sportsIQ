"""
Geometry tests for the v2 detector conventions.

These use synthetic landmark coordinates with KNOWN geometry. That is not
fabricated data - it is the standard way to test a geometric function: we
assert that a torso we constructed to be vertical measures as vertical. No
claim about real badminton performance is made anywhere in this file.
"""

from types import SimpleNamespace

import math
import pytest

from app.services.technique import comparison
from scripts.analyze_badminton_video_rule_based import (
    _classify_shot,
    _frame_angles,
    _wrap_to_quadrant,
)


def _landmarks(**points) -> list[SimpleNamespace]:
    """Build a 33-slot landmark list; only the indices we set matter."""
    lms = [SimpleNamespace(x=0.0, y=0.0, z=0.0) for _ in range(33)]
    for index, (x, y, z) in points.items():
        lms[int(index)] = SimpleNamespace(x=x, y=y, z=z)
    return lms


# Textbook overhead smash. MediaPipe image coords: x right, y DOWN.
TEXTBOOK_SMASH = _landmarks(**{
    "11": (0.45, 0.40, 0.0),   # left_shoulder
    "12": (0.55, 0.40, 0.0),   # right_shoulder
    "14": (0.60, 0.28, 0.0),   # right_elbow, above shoulder
    "16": (0.62, 0.14, 0.0),   # right_wrist, high overhead
    "23": (0.47, 0.62, 0.0),   # left_hip
    "24": (0.55, 0.62, 0.05),  # right_hip
    "26": (0.56, 0.80, 0.0),   # right_knee
    "28": (0.57, 0.97, 0.0),   # right_ankle
})

# Same body, arm dropped below the shoulder line and torso leaning hard.
LOW_ARM_LEANING = _landmarks(**{
    "11": (0.40, 0.45, 0.0),
    "12": (0.52, 0.50, 0.0),
    "14": (0.58, 0.62, 0.0),
    "16": (0.66, 0.70, 0.0),
    "23": (0.35, 0.70, 0.0),
    "24": (0.50, 0.72, 0.0),
    "26": (0.52, 0.85, 0.0),
    "28": (0.45, 0.97, 0.0),
})


def test_upright_torso_measures_near_zero_not_ninety():
    """
    The v1 regression. torso_inclination is deviation from VERTICAL, so an
    upright torso must be ~0. v1 measured from the horizontal and returned
    ~90 against a template of 12 - a guaranteed 78 deg error on every clip,
    which is what floored technique_score at 0.0.
    """
    angles = _frame_angles(TEXTBOOK_SMASH)
    assert angles["torso_inclination"] < 10.0


def test_v1_convention_bug_is_fixed_end_to_end():
    """A textbook smash must not score like bad technique."""
    angles = _frame_angles(TEXTBOOK_SMASH)
    result = comparison.compare(angles)
    assert result is not None
    # v1 produced 24.8 for this exact pose (and 0.0 for slightly worse ones).
    assert result.overall_similarity > 70.0
    assert result.level in {"INTERMEDIATE", "ADVANCED", "ELITE_REFERENCE_LIKE"}


def test_scoring_discriminates_good_from_poor_form():
    good = comparison.compare(_frame_angles(TEXTBOOK_SMASH))
    poor = comparison.compare(_frame_angles(LOW_ARM_LEANING))
    assert good is not None and poor is not None
    assert good.overall_similarity > poor.overall_similarity


def test_raised_arm_gives_positive_elevation_dropped_arm_negative():
    assert _frame_angles(TEXTBOOK_SMASH)["shoulder_elevation"] > 0
    assert _frame_angles(LOW_ARM_LEANING)["shoulder_elevation"] < 0


def test_elbow_angle_is_interior_and_bounded():
    elbow = _frame_angles(TEXTBOOK_SMASH)["elbow_angle"]
    assert 0.0 <= elbow <= 180.0


def test_hip_shoulder_separation_never_uses_depth():
    """
    Changing only z must not change the separation value - v1 computed this
    feature from MediaPipe's non-metric z and collapsed to 90 whenever z was
    near zero.
    """
    baseline = _frame_angles(TEXTBOOK_SMASH)["hip_shoulder_separation"]
    shifted = _landmarks(**{
        "11": (0.45, 0.40, 0.9), "12": (0.55, 0.40, -0.9),
        "14": (0.60, 0.28, 0.5), "16": (0.62, 0.14, -0.5),
        "23": (0.47, 0.62, 0.7), "24": (0.55, 0.62, -0.7),
        "26": (0.56, 0.80, 0.0), "28": (0.57, 0.97, 0.0),
    })
    assert _frame_angles(shifted)["hip_shoulder_separation"] == pytest.approx(baseline, abs=0.01)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(0.0, 0.0), (15.0, 15.0), (-15.0, 15.0), (170.0, 10.0), (345.0, 15.0), (90.0, 90.0)],
)
def test_wrap_to_quadrant(raw, expected):
    assert _wrap_to_quadrant(raw) == pytest.approx(expected, abs=0.001)


def test_degenerate_landmarks_yield_nan_not_zero():
    """
    All-zero landmarks give a zero-denominator angle. Returning 0.0 there
    would be scored as a real measurement 165 deg away from the reference;
    NaN is excluded from comparison instead.
    """
    angles = _frame_angles(_landmarks())
    assert math.isnan(angles["elbow_angle"])


def test_classify_shot_preserves_v1_rules():
    smash_angles = {"knee_angle": 140.0, "shoulder_elevation": 70.0, "elbow_angle": 165.0}
    assert _classify_shot(smash_angles, wrist_peak=0.20) == "JUMP_SMASH"

    stick_angles = {"knee_angle": 175.0, "shoulder_elevation": 70.0, "elbow_angle": 165.0}
    assert _classify_shot(stick_angles, wrist_peak=0.20) == "STICK_SMASH"

    clear_angles = {"knee_angle": 175.0, "shoulder_elevation": 70.0, "elbow_angle": 165.0}
    assert _classify_shot(clear_angles, wrist_peak=0.01) == "FH_CLEAR"

    drop_angles = {"knee_angle": 175.0, "shoulder_elevation": 10.0, "elbow_angle": 90.0}
    assert _classify_shot(drop_angles, wrist_peak=0.01) == "FH_DROP"

    drive_angles = {"knee_angle": 175.0, "shoulder_elevation": 10.0, "elbow_angle": 160.0}
    assert _classify_shot(drive_angles, wrist_peak=0.01) == "FH_DRIVE"


def test_classify_shot_survives_nan_features():
    nan_angles = {"knee_angle": float("nan"), "shoulder_elevation": float("nan"),
                  "elbow_angle": float("nan")}
    assert _classify_shot(nan_angles, wrist_peak=0.01) == "FH_DRIVE"
    assert _classify_shot(nan_angles, wrist_peak=0.5) == "STICK_SMASH"
