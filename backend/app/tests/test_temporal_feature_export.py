import csv

from app.ml.features.temporal import extract_temporal_features
from app.ml.pose.sequence import ArmPose, LandmarkSample, PoseFrame, PoseSequence
from app.ml.scripts.export_temporal_features import (
    build_parser,
    select_feature_frames,
    write_feature_csv,
)


def _landmark(x: float | None, y: float | None, z: float | None = 0.0):
    present = x is not None and y is not None and z is not None
    return LandmarkSample(present, x, y, z, 0.9, 0.9)


def _sequence() -> PoseSequence:
    right = ArmPose(
        _landmark(0.4, 0.4, 0.1),
        _landmark(0.5, 0.5, 0.2),
        _landmark(0.6, 0.5, 0.3),
        90.0,
    )
    missing = ArmPose(_landmark(None, None, None), _landmark(None, None, None),
                      _landmark(None, None, None), None)
    return PoseSequence(
        (
            PoseFrame(0, 0, missing, right),
            PoseFrame(1, 100, missing, right),
        ),
        30.0,
        "right",
    )


def test_select_feature_frames_is_inclusive():
    features = extract_temporal_features(_sequence())
    selected = select_feature_frames(features.frames, 1, 1)

    assert [frame.frame_index for frame in selected] == [1]


def test_feature_csv_preserves_missing_values(tmp_path):
    features = extract_temporal_features(_sequence())
    output = tmp_path / "features.csv"
    write_feature_csv(list(features.frames), output)

    with output.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    assert rows[0]["wrist_velocity_normalized_per_second"] == ""
    assert rows[0]["wrist_x"] == "0.6"
    assert rows[1]["wrist_velocity_normalized_per_second"] == "0.0"
    assert rows[1]["racket_arm_quality_status"] == "reliable"


def test_parser_accepts_video_csv_range_and_racket_side():
    args = build_parser().parse_args([
        "clip.mp4",
        "pose.csv",
        "--output-dir",
        "out",
        "--frame-range",
        "37",
        "68",
        "--racket-side",
        "right",
    ])

    assert args.frame_range == [37, 68]
    assert args.racket_side == "right"
