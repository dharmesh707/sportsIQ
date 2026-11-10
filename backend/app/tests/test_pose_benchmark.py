from pathlib import Path

import numpy as np

from scripts.pose_benchmark import (
    COMMON_JOINTS,
    DecodedFrame,
    FrameResult,
    Keypoint,
    _ranges,
    _result_summary,
    _timestamp_ms,
    _from_points,
    build_parser,
)


def test_timestamp_indices_are_strict_and_preserved():
    timestamps = []
    previous = None
    for index in range(4):
        previous = _timestamp_ms(index, 1000.0, previous)
        timestamps.append(previous)
    assert timestamps == [0, 1, 2, 3]


def test_invalid_fps_is_rejected():
    for fps in (0.0, -1.0, float("nan"), float("inf")):
        try:
            _timestamp_ms(0, fps, None)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected invalid FPS to fail: {fps!r}")


def test_missing_ranges_and_keypoint_coverage_are_reported():
    empty = {name: Keypoint(None, None, None, None) for name in COMMON_JOINTS}
    valid = dict(empty)
    valid["left_shoulder"] = Keypoint(0.5, 0.5, None, 0.9)
    results = [
        FrameResult(0, 0, 2.0, True, valid),
        FrameResult(1, 40, 3.0, False, empty),
        FrameResult(2, 80, 4.0, False, empty),
        FrameResult(4, 160, 5.0, True, valid),
    ]
    summary = _result_summary(results)
    assert summary["missing_detection_ranges"] == [[1, 2]]
    assert summary["valid_keypoints"]["left_shoulder"] == 2
    assert summary["latency_ms"]["median"] == 3.5


def test_ranges_are_deterministic_and_contiguous():
    assert _ranges([5, 2, 3, 9, 9]) == [[2, 3], [5, 5], [9, 9]]


def test_parser_accepts_multiple_estimators():
    args = build_parser().parse_args(["video.mp4", "--estimators", "mediapipe", "yolo"])
    assert args.estimators == ["mediapipe", "yolo"]


def test_normalized_points_use_canonical_coordinates_and_preserve_source_values():
    points = np.zeros((1, 3), dtype=float)
    points[0] = (0.25, 0.5, -0.3)
    result = _from_points(
        points,
        [0.8],
        {"left_shoulder": 0},
        "normalized_image",
        640,
        480,
    )["left_shoulder"]

    assert (result.x, result.y, result.z) == (0.25, 0.5, -0.3)
    assert (result.source_x, result.source_y) == (0.25, 0.5)
    assert result.confidence == 0.8


def test_pixel_points_convert_to_the_same_canonical_coordinates():
    points = np.array([[160.0, 240.0, 12.0]])
    result = _from_points(
        points,
        [0.7],
        {"left_shoulder": 0},
        "pixel_image",
        640,
        480,
    )["left_shoulder"]

    assert (result.x, result.y) == (0.25, 0.5)
    assert (result.source_x, result.source_y) == (160.0, 240.0)
    assert result.z == 12.0
    assert result.confidence == 0.7


def test_missing_points_remain_missing_without_fabricated_confidence():
    result = _from_points(
        np.array([[np.nan, 10.0, 1.0]]),
        [None],
        {"left_shoulder": 0},
        "pixel_image",
        640,
        480,
    )["left_shoulder"]

    assert not result.available
    assert result.x is None
    assert result.y is None
    assert result.source_x is None
    assert result.source_y is None
    assert result.confidence is None
