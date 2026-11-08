import csv

from app.ml.scripts.analyze_temporal_depth import (
    DepthObservation,
    select_frame_range,
    write_depth_csv,
)


def _observation(frame_index: int, elbow_z: float | None = 0.2) -> DepthObservation:
    return DepthObservation(
        frame_index=frame_index,
        timestamp_ms=frame_index * 33,
        shoulder_x=0.5,
        shoulder_y=0.4,
        shoulder_z=0.1,
        elbow_x=0.6,
        elbow_y=0.5,
        elbow_z=elbow_z,
        wrist_x=0.7,
        wrist_y=0.6,
        wrist_z=0.3,
        angle_2d=100.0,
        angle_3d=130.0,
        disagreement=30.0,
        disagreement_warning=False,
        racket_arm_quality_status="reliable",
    )


def test_selects_inclusive_frame_range():
    selected = select_frame_range(
        [_observation(36), _observation(37), _observation(68), _observation(69)],
        37,
        68,
    )

    assert [item.frame_index for item in selected] == [37, 68]


def test_depth_csv_preserves_missing_values_and_exports_fields(tmp_path):
    output = tmp_path / "depth.csv"
    write_depth_csv([_observation(37, elbow_z=None)], output)

    with output.open(newline="", encoding="utf-8") as file:
        row = next(csv.DictReader(file))
    assert row["right_elbow_z"] == ""
    assert row["right_elbow_angle_2d_degrees"] == "100.0"
    assert row["right_elbow_angle_disagreement_warning"] == "False"
