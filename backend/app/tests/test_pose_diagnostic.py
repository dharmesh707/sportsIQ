from app.ml.pose.sequence import ArmPose, LandmarkSample, PoseFrame, PoseSequence
from app.ml.scripts.diagnose_pose_sequence import (
    CsvObservation,
    build_parser,
    detect_angle_jumps,
    select_frame_indices,
    synchronize_observations,
)


def _arm() -> ArmPose:
    landmark = LandmarkSample(present=True, x=0.5, y=0.5, z=0.0, visibility=0.9)
    return ArmPose(landmark, landmark, landmark, 120.0)


def test_synchronizes_csv_rows_to_nearest_pose_timestamp():
    sequence = PoseSequence(
        frames=(
            PoseFrame(0, 0, _arm(), _arm()),
            PoseFrame(1, 100, _arm(), _arm()),
        ),
        fps=10.0,
        racket_side="unknown",
    )
    rows = [
        CsvObservation(10, 1, 120.0, 130.0, 120.0, 130.0, {}, {}),
        CsvObservation(11, 99, 121.0, 131.0, 121.0, 131.0, {}, {}),
    ]

    matches = synchronize_observations(sequence, rows, tolerance_ms=2)

    assert [match.pose_frame.frame_index for match in matches] == [0, 1]
    assert [match.timestamp_delta_ms for match in matches] == [1, 1]


def test_missing_angles_break_jump_detection():
    rows = [
        CsvObservation(0, 0, 100.0, None, 100.0, None, {}, {}),
        CsvObservation(1, 33, None, 130.0, None, 130.0, {}, {}),
        CsvObservation(2, 66, 140.0, 160.0, 140.0, 160.0, {}, {}),
    ]

    jumps = detect_angle_jumps(rows, threshold_degrees=30.0)

    assert jumps == []


def test_detects_jumps_for_consecutive_valid_values_only():
    rows = [
        CsvObservation(0, 0, 100.0, 100.0, 100.0, 100.0, {}, {}),
        CsvObservation(1, 33, 131.0, 131.0, 131.0, 131.0, {}, {}),
        CsvObservation(2, 66, 100.0, 100.0, 100.0, 100.0, {}, {}),
    ]

    jumps = detect_angle_jumps(rows)

    assert len(jumps) == 4
    assert {jump.side for jump in jumps} == {"left", "right"}
    assert all(jump.change_degrees == 31.0 for jump in jumps)


def test_selects_requested_frame_indices_only():
    sequence = PoseSequence(
        frames=(
            PoseFrame(33, 33, _arm(), _arm()),
            PoseFrame(47, 47, _arm(), _arm()),
        ),
        fps=30.0,
        racket_side="unknown",
    )
    rows = [
        CsvObservation(33, 33, 120.0, 120.0, 120.0, 120.0, {}, {}),
        CsvObservation(47, 47, 120.0, 120.0, 120.0, 120.0, {}, {}),
    ]
    synchronized = synchronize_observations(sequence, rows)

    selected = select_frame_indices(synchronized, [47])

    assert [item.pose_frame.frame_index for item in selected] == [47]


def test_parser_accepts_frame_range_and_export_mode():
    args = build_parser().parse_args([
        "video.mp4",
        "poses.csv",
        "--output-dir",
        "out",
        "--frame-range",
        "37",
        "68",
        "--export-frames",
    ])

    assert args.frame_range == [37, 68]
    assert args.export_frames is True


def test_parser_rejects_both_frame_selection_modes():
    parser = build_parser()

    try:
        parser.parse_args([
            "video.mp4",
            "poses.csv",
            "--output-dir",
            "out",
            "--frames",
            "37",
            "--frame-range",
            "40",
            "41",
        ])
    except SystemExit as error:
        assert error.code == 2
    else:
        raise AssertionError("Expected mutually exclusive frame selectors to fail")
