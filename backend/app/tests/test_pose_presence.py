import csv

import pytest

from app.ml.pose.presence import (
    load_presence_review,
    presence_for_frame,
    present_intervals,
)
from app.ml.pose.sequence import ArmPose, LandmarkSample, PoseFrame


def test_missing_pose_defaults_to_uncertain():
    missing = LandmarkSample(present=False)
    frame = PoseFrame(
        frame_index=12,
        timestamp_ms=400,
        left=ArmPose(missing, missing, missing, None),
        right=ArmPose(missing, missing, missing, None),
    )

    assert frame.player_presence == "UNCERTAIN"
    assert presence_for_frame(12) == "UNCERTAIN"


def test_explicit_reviewed_presence_values_are_preserved(tmp_path):
    path = tmp_path / "presence.csv"
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=("frame_index", "player_presence", "notes"),
        )
        writer.writeheader()
        writer.writerows([
            {"frame_index": "4", "player_presence": "PLAYER_PRESENT", "notes": "visible"},
            {"frame_index": "5", "player_presence": "PLAYER_ABSENT", "notes": "buffer"},
        ])

    reviewed = load_presence_review(path)

    assert presence_for_frame(4, reviewed) == "PLAYER_PRESENT"
    assert presence_for_frame(5, reviewed) == "PLAYER_ABSENT"
    assert presence_for_frame(6, reviewed) == "UNCERTAIN"


def test_present_intervals_preserve_inclusive_source_indices():
    reviewed = {
        10: "PLAYER_PRESENT",
        11: "PLAYER_PRESENT",
        12: "PLAYER_ABSENT",
        13: "PLAYER_PRESENT",
        15: "PLAYER_PRESENT",
        16: "UNCERTAIN",
    }

    intervals = present_intervals([10, 11, 12, 13, 14, 15, 16], reviewed)

    assert [(item.start_frame, item.end_frame) for item in intervals] == [
        (10, 11),
        (13, 13),
        (15, 15),
    ]


def test_present_intervals_handle_gaps_and_uncertain_frames():
    reviewed = {
        20: "PLAYER_PRESENT",
        21: "PLAYER_PRESENT",
        23: "PLAYER_PRESENT",
        24: "UNCERTAIN",
        25: "PLAYER_PRESENT",
    }

    intervals = present_intervals([20, 21, 22, 23, 24, 25], reviewed)

    assert [(item.start_frame, item.end_frame) for item in intervals] == [
        (20, 21),
        (23, 23),
        (25, 25),
    ]


def test_invalid_presence_status_is_rejected(tmp_path):
    path = tmp_path / "presence.csv"
    path.write_text(
        "frame_index,player_presence,notes\n1,maybe,\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unsupported player_presence"):
        load_presence_review(path)
