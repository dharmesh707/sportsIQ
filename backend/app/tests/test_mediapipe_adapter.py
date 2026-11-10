from types import SimpleNamespace

import pytest

from app.ml.pose.canonical import (
    CANONICAL_KEYPOINT_NAMES,
    FramePoseObservation,
)
from app.ml.pose.mediapipe_adapter import (
    MEDIAPIPE_LANDMARK_INDICES,
    mediapipe_landmarks_to_frame,
)


def _landmark(
    x=0.25,
    y=0.5,
    z=-0.1,
    visibility=0.9,
    presence=0.8,
):
    return SimpleNamespace(
        x=x,
        y=y,
        z=z,
        visibility=visibility,
        presence=presence,
    )


def _landmarks():
    return [
        _landmark(
            x=index / 100,
            y=index / 200,
            z=-index / 1000,
        )
        for index in range(33)
    ]


def test_converts_full_mediapipe_pose_to_canonical_frame():
    frame = mediapipe_landmarks_to_frame(
        _landmarks(),
        frame_index=10,
        timestamp_ms=400,
        width_px=608,
        height_px=1080,
    )

    assert isinstance(frame, FramePoseObservation)
    assert set(frame.keypoints) == set(CANONICAL_KEYPOINT_NAMES)
    assert len(frame.keypoints) == 21

    left_shoulder = frame.keypoints["left_shoulder"]

    assert left_shoulder.present is True
    assert left_shoulder.x_norm == pytest.approx(0.11)
    assert left_shoulder.y_norm == pytest.approx(0.055)
    assert left_shoulder.z_native == pytest.approx(-0.011)

    assert (
        left_shoulder.source_coordinate_system
        == "mediapipe_normalized_image"
    )


def test_preserves_visibility_and_presence():
    landmarks = _landmarks()
    landmarks[15] = _landmark(
        visibility=0.72,
        presence=0.63,
    )

    frame = mediapipe_landmarks_to_frame(
        landmarks,
        frame_index=0,
        timestamp_ms=0,
        width_px=608,
        height_px=1080,
    )

    wrist = frame.keypoints["left_wrist"]

    assert wrist.visibility == pytest.approx(0.72)
    assert wrist.presence == pytest.approx(0.63)


def test_missing_detection_produces_explicit_missing_keypoints():
    frame = mediapipe_landmarks_to_frame(
        None,
        frame_index=0,
        timestamp_ms=0,
        width_px=608,
        height_px=1080,
    )

    assert len(frame.keypoints) == 21
    assert all(
        not observation.present
        for observation in frame.keypoints.values()
    )


def test_short_landmark_list_marks_unavailable_points_missing():
    landmarks = _landmarks()[:16]

    frame = mediapipe_landmarks_to_frame(
        landmarks,
        frame_index=0,
        timestamp_ms=0,
        width_px=608,
        height_px=1080,
    )

    assert frame.keypoints["left_wrist"].present is True
    assert not frame.keypoints["right_wrist"].present
    assert not frame.keypoints["left_hip"].present


def test_invalid_xy_coordinates_mark_landmark_missing():
    landmarks = _landmarks()
    landmarks[15] = _landmark(x=float("nan"))

    frame = mediapipe_landmarks_to_frame(
        landmarks,
        frame_index=0,
        timestamp_ms=0,
        width_px=608,
        height_px=1080,
    )

    wrist = frame.keypoints["left_wrist"]

    assert wrist.present is False
    assert wrist.x_norm is None
    assert wrist.y_norm is None


def test_invalid_confidence_is_not_preserved():
    landmarks = _landmarks()
    landmarks[15] = _landmark(
        visibility=1.5,
        presence=float("nan"),
    )

    frame = mediapipe_landmarks_to_frame(
        landmarks,
        frame_index=0,
        timestamp_ms=0,
        width_px=608,
        height_px=1080,
    )

    wrist = frame.keypoints["left_wrist"]

    assert wrist.present is True
    assert wrist.visibility is None
    assert wrist.presence is None


def test_preserves_frame_metadata():
    frame = mediapipe_landmarks_to_frame(
        _landmarks(),
        frame_index=12,
        timestamp_ms=480,
        width_px=608,
        height_px=1080,
        player_presence="PLAYER_PRESENT",
    )

    assert frame.frame_index == 12
    assert frame.timestamp_ms == 480
    assert frame.width_px == 608
    assert frame.height_px == 1080
    assert frame.player_presence == "PLAYER_PRESENT"


def test_mapping_matches_canonical_keypoint_names():
    assert set(MEDIAPIPE_LANDMARK_INDICES) == set(
        CANONICAL_KEYPOINT_NAMES
    )

    assert len(set(MEDIAPIPE_LANDMARK_INDICES.values())) == 21