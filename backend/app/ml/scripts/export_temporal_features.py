"""Export temporal pose features from an existing validation sequence CSV."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

from app.ml.features.temporal import TemporalFeatureFrame, extract_temporal_features
from app.ml.pose.sequence import (
    ArmPose,
    LandmarkSample,
    PoseFrame,
    PoseSequence,
    RacketSide,
)

FEATURE_COLUMNS = [
    "frame_index",
    "timestamp_ms",
    "shoulder_x",
    "shoulder_y",
    "shoulder_z",
    "elbow_x",
    "elbow_y",
    "elbow_z",
    "wrist_x",
    "wrist_y",
    "wrist_z",
    "shoulder_visibility",
    "shoulder_presence",
    "elbow_visibility",
    "elbow_presence",
    "wrist_visibility",
    "wrist_presence",
    "elbow_angle_2d_degrees",
    "elbow_angle_3d_degrees",
    "shoulder_elevation_degrees",
    "wrist_displacement_normalized",
    "wrist_velocity_normalized_per_second",
    "elbow_angular_velocity_degrees_per_second",
    "quality_status",
    "quality_reasons",
    "racket_arm_quality_status",
    "racket_arm_quality_reasons",
]


def _float(value: str | None) -> float | None:
    if value is None or value.strip() == "":
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def _int(value: str, field: str) -> int:
    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f"Invalid {field}: {value!r}") from error


def _landmark(row: dict[str, str], side: str, joint: str) -> LandmarkSample:
    prefix = f"{side}_{joint}"
    x = _float(row.get(f"{prefix}_x"))
    y = _float(row.get(f"{prefix}_y"))
    z = _float(row.get(f"{prefix}_z"))
    present = x is not None and y is not None and z is not None
    return LandmarkSample(
        present=present,
        x=x if present else None,
        y=y if present else None,
        z=z if present else None,
        visibility=_float(row.get(f"{prefix}_visibility")),
        presence=_float(row.get(f"{prefix}_presence")),
    )


def _arm(row: dict[str, str], side: str) -> ArmPose:
    return ArmPose(
        shoulder=_landmark(row, side, "shoulder"),
        elbow=_landmark(row, side, "elbow"),
        wrist=_landmark(row, side, "wrist"),
        elbow_angle_degrees=_float(row.get(f"{side}_elbow_angle_degrees")),
    )


def load_pose_sequence_csv(
    csv_path: Path,
    racket_side: RacketSide,
) -> PoseSequence:
    """Reconstruct the exported pose sequence without filling missing values."""
    frames: list[PoseFrame] = []
    with csv_path.open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            frames.append(PoseFrame(
                frame_index=_int(row["frame_index"], "frame_index"),
                timestamp_ms=_int(row["timestamp_ms"], "timestamp_ms"),
                left=_arm(row, "left"),
                right=_arm(row, "right"),
            ))
    return PoseSequence(tuple(frames), fps=0.0, racket_side=racket_side)


def select_feature_frames(
    frames: tuple[TemporalFeatureFrame, ...],
    start: int | None = None,
    end: int | None = None,
) -> list[TemporalFeatureFrame]:
    """Select an inclusive frame range while preserving source order."""
    if (start is None) != (end is None):
        raise ValueError("frame range requires both start and end")
    if start is not None and start > end:
        raise ValueError("start frame must be less than or equal to end frame")
    if start is None:
        return list(frames)
    return [frame for frame in frames if start <= frame.frame_index <= end]


def _value(value: object) -> object:
    return "" if value is None else value


def _feature_row(frame: TemporalFeatureFrame) -> dict[str, object]:
    row = {
        "frame_index": frame.frame_index,
        "timestamp_ms": frame.timestamp_ms,
        "shoulder_x": frame.shoulder_x,
        "shoulder_y": frame.shoulder_y,
        "shoulder_z": frame.shoulder_z,
        "elbow_x": frame.elbow_x,
        "elbow_y": frame.elbow_y,
        "elbow_z": frame.elbow_z,
        "wrist_x": frame.wrist_x,
        "wrist_y": frame.wrist_y,
        "wrist_z": frame.wrist_z,
        "shoulder_visibility": frame.shoulder_visibility,
        "shoulder_presence": frame.shoulder_presence,
        "elbow_visibility": frame.elbow_visibility,
        "elbow_presence": frame.elbow_presence,
        "wrist_visibility": frame.wrist_visibility,
        "wrist_presence": frame.wrist_presence,
        "elbow_angle_2d_degrees": frame.elbow_angle_2d_degrees,
        "elbow_angle_3d_degrees": frame.elbow_angle_3d_degrees,
        "shoulder_elevation_degrees": frame.shoulder_elevation_degrees,
        "wrist_displacement_normalized": frame.wrist_displacement_normalized,
        "wrist_velocity_normalized_per_second": (
            frame.wrist_velocity_normalized_per_second
        ),
        "elbow_angular_velocity_degrees_per_second": (
            frame.elbow_angular_velocity_degrees_per_second
        ),
        "quality_status": frame.quality_status,
        "quality_reasons": ";".join(frame.quality_reasons),
        "racket_arm_quality_status": frame.racket_arm_quality_status,
        "racket_arm_quality_reasons": ";".join(frame.racket_arm_quality_reasons),
    }
    return {key: _value(value) for key, value in row.items()}


def write_feature_csv(
    frames: list[TemporalFeatureFrame],
    output_path: Path,
) -> None:
    """Write temporal features with unavailable values as empty fields."""
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FEATURE_COLUMNS)
        writer.writeheader()
        writer.writerows(_feature_row(frame) for frame in frames)


def write_feature_plots(
    frames: list[TemporalFeatureFrame],
    output_path: Path,
) -> None:
    """Write trajectory, angle, velocity, and missingness diagnostics."""
    try:
        import matplotlib.pyplot as plt
    except ImportError as error:
        raise RuntimeError(
            "Plot generation requires matplotlib. Install it with "
            "`python -m pip install matplotlib`."
        ) from error

    times = [frame.timestamp_ms / 1000 for frame in frames]
    figure, axes = plt.subplots(4, 1, figsize=(11, 12), sharex=True)
    axes[0].plot(times, [frame.wrist_x for frame in frames], label="Wrist x")
    axes[0].plot(times, [frame.wrist_y for frame in frames], label="Wrist y")
    axes[0].set_ylabel("Normalized coordinate")
    axes[0].set_title("Racket-arm wrist trajectory")
    axes[0].legend()

    axes[1].plot(
        times,
        [frame.elbow_angle_2d_degrees for frame in frames],
        label="2D elbow angle",
    )
    axes[1].plot(
        times,
        [frame.elbow_angle_3d_degrees for frame in frames],
        label="3D elbow angle",
    )
    axes[1].set_ylabel("Degrees")
    axes[1].set_title("Elbow angle")
    axes[1].legend()

    axes[2].plot(
        times,
        [frame.wrist_velocity_normalized_per_second for frame in frames],
        label="Wrist velocity",
    )
    axes[2].set_ylabel("Normalized units/s")
    axes[2].set_title("Wrist velocity")
    axes[2].legend()

    feature_names = (
        "shoulder_x",
        "elbow_x",
        "wrist_x",
        "elbow_angle_2d_degrees",
        "wrist_velocity_normalized_per_second",
    )
    missing_counts = [
        sum(
            getattr(frame, name) is None
            for name in feature_names
        )
        for frame in frames
    ]
    axes[3].plot(times, missing_counts, marker=".", label="Missing feature count")
    axes[3].set_xlabel("Time (seconds)")
    axes[3].set_ylabel("Count")
    axes[3].set_title("Feature missingness")
    axes[3].set_ylim(bottom=0)
    axes[3].legend()

    for axis in axes:
        axis.grid(True, alpha=0.3)
    figure.tight_layout()
    figure.savefig(output_path, dpi=150)
    plt.close(figure)


def export_temporal_features(
    video_path: Path,
    sequence_csv: Path,
    output_dir: Path,
    racket_side: RacketSide,
    frame_range: tuple[int, int] | None = None,
) -> tuple[Path, Path]:
    """Export features from a validation CSV associated with a local video."""
    if not video_path.is_file():
        raise FileNotFoundError(f"Video file does not exist: {video_path}")
    sequence = load_pose_sequence_csv(sequence_csv, racket_side)
    features = extract_temporal_features(sequence)
    start, end = frame_range if frame_range is not None else (None, None)
    selected = select_feature_frames(features.frames, start, end)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = video_path.stem
    csv_path = output_dir / f"{stem}_temporal_features.csv"
    plot_path = output_dir / f"{stem}_temporal_features.png"
    write_feature_csv(selected, csv_path)
    write_feature_plots(selected, plot_path)
    return csv_path, plot_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export temporal pose features from a validation CSV."
    )
    parser.add_argument("video", type=Path, help="Original validation video path.")
    parser.add_argument("csv", type=Path, help="Existing pose-sequence CSV path.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for generated CSV and diagnostic plot.",
    )
    parser.add_argument(
        "--frame-range",
        nargs=2,
        type=int,
        metavar=("START", "END"),
        help="Inclusive frame range; derivatives use the full source sequence.",
    )
    parser.add_argument(
        "--racket-side",
        choices=("left", "right", "unknown"),
        default="unknown",
        help="Racket side metadata; defaults to unknown.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if not args.csv.is_file():
        raise SystemExit(f"Pose-sequence CSV does not exist: {args.csv}")
    frame_range = tuple(args.frame_range) if args.frame_range else None
    try:
        csv_path, plot_path = export_temporal_features(
            args.video,
            args.csv,
            args.output_dir,
            args.racket_side,
            frame_range,
        )
    except (FileNotFoundError, ValueError, RuntimeError) as error:
        raise SystemExit(str(error)) from error
    print(f"CSV: {csv_path}")
    print(f"Plot: {plot_path}")


if __name__ == "__main__":
    main()
