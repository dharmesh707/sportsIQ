from __future__ import annotations

from app.ml.features.full_body import preprocess_full_body_sequence
from app.ml.features.full_body_temporal import (
    extract_full_body_temporal_features,
)
from app.ml.features.joint_angles import extract_joint_angles
from app.ml.features.sequence_encoder import (
    EncodedTemporalSequence,
    encode_temporal_sequence,
)
from app.ml.pose.canonical import CanonicalPoseSequence
from app.ml.pose.canonical_slicing import (
    slice_canonical_pose_sequence,
)


def extract_encoded_clip_features(
    sequence: CanonicalPoseSequence,
    start_ms: float,
    end_ms: float,
    *,
    target_length: int = 32,
    confidence_threshold: float = 0.5,
) -> EncodedTemporalSequence:
    """
    Convert an annotated interval from a canonical source-video
    sequence into a fixed-length encoded temporal feature sequence.

    Temporal derivatives are computed after slicing so the clip
    boundaries do not use motion from outside the annotation.
    """
    clip_sequence = slice_canonical_pose_sequence(
        sequence,
        start_ms=start_ms,
        end_ms=end_ms,
    )

    if len(clip_sequence.frames) < 2:
        raise ValueError(
            "Clip must contain at least two frames to extract "
            "temporal features."
        )

    position_sequence = preprocess_full_body_sequence(
        clip_sequence,
        confidence_threshold=confidence_threshold,
    )

    angle_sequence = extract_joint_angles(
        clip_sequence,
        confidence_threshold=confidence_threshold,
    )

    temporal_sequence = extract_full_body_temporal_features(
        position_sequence,
        angle_sequence,
    )

    return encode_temporal_sequence(
        temporal_sequence,
        target_length=target_length,
    )