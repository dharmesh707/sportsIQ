"""Export and plot a MediaPipe badminton pose sequence for offline review."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

from app.ml.pose.sequence import ArmPose, PoseSequence, extract_pose_sequence
from app.ml.pose.quality import (
    DEFAULT_CONFIDENCE_THRESHOLD,
    assess_arm_roles,
    assess_frame_quality,
    frame_quality_coverage,
)

DEFAULT_ANGLE_DISAGREEMENT_WARNING_THRESHOLD = 30.0

CSV_COLUMNS = [
    "frame_index",
    "timestamp_ms",
    "frame_quality_status",
    "frame_quality_reasons",
    "racket_arm_quality_status",
    "racket_arm_quality_reasons",
    "non_racket_arm_quality_status",
    "non_racket_arm_quality_reasons",
    "left_elbow_angle_degrees",
    "right_elbow_angle_degrees",
    "left_elbow_angle_2d_degrees",
    "right_elbow_angle_2d_degrees",
    "left_elbow_angle_disagreement_degrees",
    "right_elbow_angle_disagreement_degrees",
    "left_elbow_angle_disagreement_warning",
    "right_elbow_angle_disagreement_warning",
    "left_shoulder_x",
    "left_shoulder_y",
    "left_shoulder_z",
    "left_shoulder_visibility",
    "left_shoulder_presence",
    "left_elbow_x",
    "left_elbow_y",
    "left_elbow_z",
    "left_elbow_visibility",
    "left_elbow_presence",
    "left_wrist_x",
    "left_wrist_y",
    "left_wrist_z",
    "left_wrist_visibility",
    "left_wrist_presence",
    "right_shoulder_x",
    "right_shoulder_y",
    "right_shoulder_z",
    "right_shoulder_visibility",
    "right_shoulder_presence",
    "right_elbow_x",
    "right_elbow_y",
    "right_elbow_z",
    "right_elbow_visibility",
    "right_elbow_presence",
    "right_wrist_x",
    "right_wrist_y",
    "right_wrist_z",
    "right_wrist_visibility",
    "right_wrist_presence",
]


def _value(value: float | int | None) -> float | int | str:
    """Keep missing values empty in CSV output rather than fabricating data."""
    return "" if value is None else value


def _landmark_columns(landmark) -> dict[str, float | int | str]:
    return {
        "x": _value(landmark.x),
        "y": _value(landmark.y),
        "z": _value(landmark.z),
        "visibility": _value(landmark.visibility),
        "presence": _value(landmark.presence),
    }


def calculate_elbow_angle_2d(arm: ArmPose) -> float | None:
    """Calculate a diagnostic elbow angle from valid x/y landmark coordinates."""
    landmarks = (arm.shoulder, arm.elbow, arm.wrist)
    if not all(
        landmark.present
        and landmark.x is not None
        and landmark.y is not None
        and math.isfinite(landmark.x)
        and math.isfinite(landmark.y)
        for landmark in landmarks
    ):
        return None

    first_vector = (
        arm.shoulder.x - arm.elbow.x,
        arm.shoulder.y - arm.elbow.y,
    )
    last_vector = (
        arm.wrist.x - arm.elbow.x,
        arm.wrist.y - arm.elbow.y,
    )
    denominator = math.hypot(*first_vector) * math.hypot(*last_vector)
    if not math.isfinite(denominator) or denominator <= 0:
        return None
    cosine = (
        first_vector[0] * last_vector[0]
        + first_vector[1] * last_vector[1]
    ) / denominator
    if not math.isfinite(cosine):
        return None
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


def calculate_angle_disagreement(
    angle_3d: float | None,
    angle_2d: float | None,
) -> float | None:
    """Return the absolute 2D/3D difference when both angles are finite."""
    if (
        angle_3d is None
        or angle_2d is None
        or not math.isfinite(angle_3d)
        or not math.isfinite(angle_2d)
    ):
        return None
    return abs(angle_3d - angle_2d)


def angle_disagreement_warning(
    angle_3d: float | None,
    angle_2d: float | None,
    threshold_degrees: float = DEFAULT_ANGLE_DISAGREEMENT_WARNING_THRESHOLD,
) -> bool:
    """Flag disagreement strictly above the diagnostic threshold."""
    if not math.isfinite(threshold_degrees) or threshold_degrees < 0:
        raise ValueError("threshold_degrees must be finite and non-negative")
    disagreement = calculate_angle_disagreement(angle_3d, angle_2d)
    return disagreement is not None and disagreement > threshold_degrees


def write_sequence_csv(
    sequence: PoseSequence,
    output_path: Path,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    angle_disagreement_threshold: float = (
        DEFAULT_ANGLE_DISAGREEMENT_WARNING_THRESHOLD
    ),
) -> float:
    """Write bilateral angles, coordinates, and confidence metadata to CSV."""
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for frame in sequence.frames:
            quality = assess_frame_quality(frame, confidence_threshold)
            racket_quality, non_racket_quality = assess_arm_roles(
                frame,
                sequence.racket_side,
                confidence_threshold,
            )
            left_angle_2d = calculate_elbow_angle_2d(frame.left)
            right_angle_2d = calculate_elbow_angle_2d(frame.right)
            row: dict[str, float | int | str] = {
                "frame_index": frame.frame_index,
                "timestamp_ms": frame.timestamp_ms,
                "frame_quality_status": "reliable" if quality.reliable else "unreliable",
                "frame_quality_reasons": ";".join(quality.reasons),
                "racket_arm_quality_status": racket_quality.status,
                "racket_arm_quality_reasons": ";".join(racket_quality.reasons),
                "non_racket_arm_quality_status": non_racket_quality.status,
                "non_racket_arm_quality_reasons": ";".join(non_racket_quality.reasons),
                "left_elbow_angle_degrees": _value(frame.left.elbow_angle_degrees),
                "right_elbow_angle_degrees": _value(frame.right.elbow_angle_degrees),
                "left_elbow_angle_2d_degrees": _value(
                    left_angle_2d
                ),
                "right_elbow_angle_2d_degrees": _value(
                    right_angle_2d
                ),
                "left_elbow_angle_disagreement_degrees": _value(
                    calculate_angle_disagreement(
                        frame.left.elbow_angle_degrees,
                        left_angle_2d,
                    )
                ),
                "right_elbow_angle_disagreement_degrees": _value(
                    calculate_angle_disagreement(
                        frame.right.elbow_angle_degrees,
                        right_angle_2d,
                    )
                ),
                "left_elbow_angle_disagreement_warning": angle_disagreement_warning(
                    frame.left.elbow_angle_degrees,
                    left_angle_2d,
                    angle_disagreement_threshold,
                ),
                "right_elbow_angle_disagreement_warning": angle_disagreement_warning(
                    frame.right.elbow_angle_degrees,
                    right_angle_2d,
                    angle_disagreement_threshold,
                ),
            }
            for side, arm in (("left", frame.left), ("right", frame.right)):
                for joint in ("shoulder", "elbow", "wrist"):
                    values = _landmark_columns(getattr(arm, joint))
                    row.update({
                        f"{side}_{joint}_{key}": value
                        for key, value in values.items()
                    })
            writer.writerow(row)
    return frame_quality_coverage(
        sequence.frames,
        confidence_threshold,
    )


def write_angle_plot(sequence: PoseSequence, output_path: Path) -> None:
    """Plot both elbow-angle series, preserving missing observations as gaps."""
    try:
        import matplotlib.pyplot as plt
    except ImportError as error:
        raise RuntimeError(
            "Plot generation requires matplotlib. Install it with "
            "`python -m pip install matplotlib`."
        ) from error

    times = [frame.timestamp_ms / 1000 for frame in sequence.frames]
    left_angles = [
        frame.left.elbow_angle_degrees for frame in sequence.frames
    ]
    right_angles = [
        frame.right.elbow_angle_degrees for frame in sequence.frames
    ]

    figure, axis = plt.subplots(figsize=(10, 5))
    axis.plot(times, left_angles, label="Left elbow", marker=".", linewidth=1)
    axis.plot(times, right_angles, label="Right elbow", marker=".", linewidth=1)
    axis.set_title("Badminton elbow angles")
    axis.set_xlabel("Time (seconds)")
    axis.set_ylabel("Elbow angle (degrees)")
    axis.grid(True, alpha=0.3)
    axis.legend()
    figure.tight_layout()
    figure.savefig(output_path, dpi=150)
    plt.close(figure)


def validate_video(
    video_path: Path,
    output_dir: Path,
    racket_side: str,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    angle_disagreement_threshold: float = (
        DEFAULT_ANGLE_DISAGREEMENT_WARNING_THRESHOLD
    ),
) -> tuple[Path, Path]:
    """Extract one video and write its CSV and plot outputs."""
    sequence = extract_pose_sequence(video_path, racket_side=racket_side)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"{video_path.stem}_pose_sequence.csv"
    plot_path = output_dir / f"{video_path.stem}_elbow_angles.png"
    coverage = write_sequence_csv(
        sequence,
        csv_path,
        confidence_threshold,
        angle_disagreement_threshold,
    )
    write_angle_plot(sequence, plot_path)
    print(f"Reliable-frame coverage: {coverage:.1%}")
    return csv_path, plot_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export and plot a bilateral MediaPipe pose sequence."
    )
    parser.add_argument("video", type=Path, help="Local video path to validate.")
    parser.add_argument(
        "--racket-side",
        choices=("left", "right", "unknown"),
        default="unknown",
        help="Racket side metadata; defaults to unknown.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for the generated CSV and PNG.",
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=DEFAULT_CONFIDENCE_THRESHOLD,
        help=f"Minimum visibility/presence confidence (default: {DEFAULT_CONFIDENCE_THRESHOLD}).",
    )
    parser.add_argument(
        "--angle-disagreement-threshold",
        type=float,
        default=DEFAULT_ANGLE_DISAGREEMENT_WARNING_THRESHOLD,
        help=(
            "2D/3D angle warning threshold in degrees "
            f"(default: {DEFAULT_ANGLE_DISAGREEMENT_WARNING_THRESHOLD})."
        ),
    )
    args = parser.parse_args()

    if not args.video.is_file():
        parser.error(f"Video file does not exist: {args.video}")
    csv_path, plot_path = validate_video(
        args.video,
        args.output_dir,
        args.racket_side,
        args.confidence_threshold,
        args.angle_disagreement_threshold,
    )
    print(f"CSV: {csv_path}")
    print(f"Plot: {plot_path}")


if __name__ == "__main__":
    main()
