from app.ml.pose.quality import (
    DEFAULT_CONFIDENCE_THRESHOLD,
    assess_arm_roles,
    assess_frame_quality,
    frame_quality_coverage,
)
from app.ml.pose.sequence import ArmPose, LandmarkSample, PoseFrame


def _arm(
    *,
    visibility: float | None = 0.9,
    presence: float | None = 0.9,
    present: bool = True,
    x: float = 0.5,
    y: float = 0.5,
) -> ArmPose:
    landmark = LandmarkSample(
        present=present,
        x=x,
        y=y,
        z=0.0,
        visibility=visibility,
        presence=presence,
    )
    return ArmPose(landmark, landmark, landmark, 90.0)


def _frame(left: ArmPose | None = None, right: ArmPose | None = None) -> PoseFrame:
    return PoseFrame(0, 0, left or _arm(), right or _arm())


def test_valid_frame_is_reliable_at_default_threshold():
    quality = assess_frame_quality(_frame(), DEFAULT_CONFIDENCE_THRESHOLD)

    assert quality.reliable
    assert quality.reasons == ()


def test_low_confidence_landmark_is_unreliable():
    quality = assess_frame_quality(_frame(left=_arm(visibility=0.49)))

    assert not quality.reliable
    assert "left_shoulder_visibility_low" in quality.reasons
    assert "left_elbow_visibility_low" in quality.reasons
    assert "left_wrist_visibility_low" in quality.reasons


def test_missing_landmark_is_unreliable():
    quality = assess_frame_quality(_frame(right=_arm(present=False)))

    assert not quality.reliable
    assert "right_shoulder_missing" in quality.reasons
    assert "right_elbow_missing" in quality.reasons
    assert "right_wrist_missing" in quality.reasons


def test_out_of_frame_landmark_is_unreliable():
    quality = assess_frame_quality(_frame(left=_arm(x=1.01, y=-0.01)))

    assert not quality.reliable
    assert "left_shoulder_out_of_frame" in quality.reasons
    assert "left_elbow_out_of_frame" in quality.reasons
    assert "left_wrist_out_of_frame" in quality.reasons


def test_coverage_counts_reliable_frames():
    frames = (_frame(), _frame(left=_arm(visibility=0.1)))

    assert frame_quality_coverage(frames) == 0.5


def test_racket_arm_can_be_reliable_when_non_racket_arm_is_missing():
    racket, non_racket = assess_arm_roles(
        _frame(right=_arm(present=False)),
        "left",
    )

    assert racket.status == "reliable"
    assert non_racket.status == "unreliable"


def test_racket_arm_is_unreliable_when_its_confidence_is_low():
    racket, non_racket = assess_arm_roles(
        _frame(left=_arm(visibility=0.4)),
        "left",
    )

    assert racket.status == "unreliable"
    assert "left_shoulder_visibility_low" in racket.reasons
    assert non_racket.status == "reliable"


def test_unknown_racket_side_does_not_guess_roles():
    racket, non_racket = assess_arm_roles(_frame(), "unknown")

    assert racket.status == "unknown"
    assert racket.reasons == ("racket_side_unknown",)
    assert non_racket.status == "unknown"
    assert non_racket.reasons == ("racket_side_unknown",)


def test_overall_quality_remains_bilateral():
    frame = _frame(right=_arm(present=False))

    assert not assess_frame_quality(frame).reliable
