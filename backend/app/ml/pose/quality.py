"""Diagnostic quality assessment for extracted pose frames."""

from __future__ import annotations

from dataclasses import dataclass

from app.ml.pose.sequence import ArmPose, PoseFrame, RacketSide

DEFAULT_CONFIDENCE_THRESHOLD = 0.5
_JOINTS = ("shoulder", "elbow", "wrist")


@dataclass(frozen=True)
class PoseQuality:
    reliable: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ArmQuality:
    status: str
    reasons: tuple[str, ...]


def assess_arm_quality(
    arm: ArmPose,
    side: str,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> ArmQuality:
    """Assess one arm's relevant landmarks."""
    if not 0.0 <= confidence_threshold <= 1.0:
        raise ValueError("confidence_threshold must be between 0 and 1")
    reasons: list[str] = []
    for joint in _JOINTS:
        landmark = getattr(arm, joint)
        label = f"{side}_{joint}"
        if not landmark.present:
            reasons.append(f"{label}_missing")
            continue
        if (
            landmark.x is None
            or landmark.y is None
            or not 0.0 <= landmark.x <= 1.0
            or not 0.0 <= landmark.y <= 1.0
        ):
            reasons.append(f"{label}_out_of_frame")
        if landmark.visibility is None:
            reasons.append(f"{label}_visibility_missing")
        elif landmark.visibility < confidence_threshold:
            reasons.append(f"{label}_visibility_low")
        if landmark.presence is None:
            reasons.append(f"{label}_presence_missing")
        elif landmark.presence < confidence_threshold:
            reasons.append(f"{label}_presence_low")
    return ArmQuality(
        status="reliable" if not reasons else "unreliable",
        reasons=tuple(reasons),
    )


def assess_arm_roles(
    frame: PoseFrame,
    racket_side: RacketSide,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> tuple[ArmQuality, ArmQuality]:
    """Assess racket and non-racket arms without guessing an unknown side."""
    if racket_side == "unknown":
        unknown = ArmQuality("unknown", ("racket_side_unknown",))
        return unknown, unknown
    if racket_side == "left":
        return (
            assess_arm_quality(frame.left, "left", confidence_threshold),
            assess_arm_quality(frame.right, "right", confidence_threshold),
        )
    if racket_side == "right":
        return (
            assess_arm_quality(frame.right, "right", confidence_threshold),
            assess_arm_quality(frame.left, "left", confidence_threshold),
        )
    raise ValueError("racket_side must be 'left', 'right', or 'unknown'")


def assess_frame_quality(
    frame: PoseFrame,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> PoseQuality:
    """Assess bilateral arm landmarks without changing their raw values."""
    if not 0.0 <= confidence_threshold <= 1.0:
        raise ValueError("confidence_threshold must be between 0 and 1")

    reasons = list(assess_arm_quality(
        frame.left, "left", confidence_threshold
    ).reasons)
    reasons.extend(assess_arm_quality(
        frame.right, "right", confidence_threshold
    ).reasons)
    return PoseQuality(reliable=not reasons, reasons=tuple(reasons))


def frame_quality_coverage(
    frames: tuple[PoseFrame, ...],
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> float:
    """Return the fraction of frames assessed as reliable."""
    if not frames:
        return 0.0
    valid_count = sum(
        assess_frame_quality(frame, confidence_threshold).reliable
        for frame in frames
    )
    return valid_count / len(frames)
