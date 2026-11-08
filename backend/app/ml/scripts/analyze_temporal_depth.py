"""Offline diagnostic analysis of MediaPipe model-relative right-arm depth."""

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DepthObservation:
    frame_index: int
    timestamp_ms: int | None
    shoulder_x: float | None
    shoulder_y: float | None
    shoulder_z: float | None
    elbow_x: float | None
    elbow_y: float | None
    elbow_z: float | None
    wrist_x: float | None
    wrist_y: float | None
    wrist_z: float | None
    angle_2d: float | None
    angle_3d: float | None
    disagreement: float | None
    disagreement_warning: bool
    racket_arm_quality_status: str

    @property
    def elbow_relative_depth(self) -> float | None:
        return _relative_depth(self.elbow_z, self.shoulder_z)

    @property
    def wrist_relative_depth(self) -> float | None:
        return _relative_depth(self.wrist_z, self.shoulder_z)


CSV_COLUMNS = [
    "frame_index",
    "timestamp_ms",
    "right_shoulder_x",
    "right_shoulder_y",
    "right_shoulder_z",
    "right_elbow_x",
    "right_elbow_y",
    "right_elbow_z",
    "right_wrist_x",
    "right_wrist_y",
    "right_wrist_z",
    "right_elbow_angle_2d_degrees",
    "right_elbow_angle_3d_degrees",
    "right_elbow_angle_disagreement_degrees",
    "right_elbow_angle_disagreement_warning",
    "racket_arm_quality_status",
]


def _float(value: str | None) -> float | None:
    if value is None or value.strip() == "":
        return None
    try:
        result = float(value)
    except ValueError:
        return None
    return result if math.isfinite(result) else None


def _relative_depth(value: float | None, shoulder: float | None) -> float | None:
    if value is None or shoulder is None:
        return None
    return value - shoulder


def load_depth_observations(csv_path: Path) -> list[DepthObservation]:
    """Load right-arm raw values and diagnostic fields without filling gaps."""
    observations: list[DepthObservation] = []
    with csv_path.open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            timestamp = row.get("timestamp_ms", "").strip()
            observations.append(DepthObservation(
                frame_index=int(row["frame_index"]),
                timestamp_ms=int(timestamp) if timestamp else None,
                shoulder_x=_float(row.get("right_shoulder_x")),
                shoulder_y=_float(row.get("right_shoulder_y")),
                shoulder_z=_float(row.get("right_shoulder_z")),
                elbow_x=_float(row.get("right_elbow_x")),
                elbow_y=_float(row.get("right_elbow_y")),
                elbow_z=_float(row.get("right_elbow_z")),
                wrist_x=_float(row.get("right_wrist_x")),
                wrist_y=_float(row.get("right_wrist_y")),
                wrist_z=_float(row.get("right_wrist_z")),
                angle_2d=_float(row.get("right_elbow_angle_2d_degrees")),
                angle_3d=_float(row.get("right_elbow_angle_degrees")),
                disagreement=_float(
                    row.get("right_elbow_angle_disagreement_degrees")
                ),
                disagreement_warning=row.get(
                    "right_elbow_angle_disagreement_warning", ""
                ).strip().lower() == "true",
                racket_arm_quality_status=row.get(
                    "racket_arm_quality_status", "unknown"
                ),
            ))
    return observations


def select_frame_range(
    observations: list[DepthObservation],
    start: int,
    end: int,
) -> list[DepthObservation]:
    """Select an inclusive frame range while preserving source order."""
    if start > end:
        raise ValueError("start frame must be less than or equal to end frame")
    return [
        observation
        for observation in observations
        if start <= observation.frame_index <= end
    ]


def write_depth_csv(
    observations: list[DepthObservation],
    output_path: Path,
) -> None:
    """Write raw right-arm values and relative depth diagnostics."""
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for observation in observations:
            writer.writerow({
                "frame_index": observation.frame_index,
                "timestamp_ms": _value(observation.timestamp_ms),
                "right_shoulder_x": _value(observation.shoulder_x),
                "right_shoulder_y": _value(observation.shoulder_y),
                "right_shoulder_z": _value(observation.shoulder_z),
                "right_elbow_x": _value(observation.elbow_x),
                "right_elbow_y": _value(observation.elbow_y),
                "right_elbow_z": _value(observation.elbow_z),
                "right_wrist_x": _value(observation.wrist_x),
                "right_wrist_y": _value(observation.wrist_y),
                "right_wrist_z": _value(observation.wrist_z),
                "right_elbow_angle_2d_degrees": _value(observation.angle_2d),
                "right_elbow_angle_3d_degrees": _value(observation.angle_3d),
                "right_elbow_angle_disagreement_degrees": _value(
                    observation.disagreement
                ),
                "right_elbow_angle_disagreement_warning": (
                    observation.disagreement_warning
                ),
                "racket_arm_quality_status": observation.racket_arm_quality_status,
            })


def write_depth_plot(
    observations: list[DepthObservation],
    output_path: Path,
) -> None:
    """Plot model-relative depth and angle disagreement diagnostics."""
    try:
        import matplotlib.pyplot as plt
    except ImportError as error:
        raise RuntimeError(
            "Plot generation requires matplotlib. Install it with "
            "`python -m pip install matplotlib`."
        ) from error

    x_values = [item.frame_index for item in observations]
    figure, (depth_axis, angle_axis) = plt.subplots(2, 1, figsize=(11, 8), sharex=True)
    depth_axis.plot(x_values, [0.0] * len(observations), label="Shoulder (relative)", marker=".")
    depth_axis.plot(
        x_values,
        [item.elbow_relative_depth for item in observations],
        label="Elbow - shoulder z",
        marker=".",
    )
    depth_axis.plot(
        x_values,
        [item.wrist_relative_depth for item in observations],
        label="Wrist - shoulder z",
        marker=".",
    )
    depth_axis.set_ylabel("Model-relative z")
    depth_axis.set_title("Right-arm model-relative depth")
    depth_axis.legend()
    depth_axis.grid(True, alpha=0.3)

    angle_axis.plot(x_values, [item.angle_2d for item in observations], label="2D angle")
    angle_axis.plot(x_values, [item.angle_3d for item in observations], label="3D angle")
    warning_frames = [
        item.frame_index for item in observations if item.disagreement_warning
    ]
    warning_angles = [
        item.angle_3d for item in observations if item.disagreement_warning
    ]
    angle_axis.scatter(
        warning_frames,
        warning_angles,
        color="red",
        marker="x",
        label="Disagreement warning",
    )
    angle_axis.set_xlabel("Frame index")
    angle_axis.set_ylabel("Elbow angle (degrees)")
    angle_axis.legend()
    angle_axis.grid(True, alpha=0.3)
    figure.suptitle("MediaPipe z is model-relative, not calibrated physical depth")
    figure.tight_layout()
    figure.savefig(output_path, dpi=150)
    plt.close(figure)


def _value(value: float | int | None) -> float | int | str:
    return "" if value is None else value


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze model-relative right-arm depth from a validation CSV."
    )
    parser.add_argument("csv", type=Path, help="Validation pose-sequence CSV.")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--frame-range", type=int, nargs=2, required=True)
    args = parser.parse_args()
    observations = select_frame_range(
        load_depth_observations(args.csv),
        args.frame_range[0],
        args.frame_range[1],
    )
    if not observations:
        parser.error("No observations found in the requested frame range.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_csv = args.output_dir / (
        f"temporal_depth_{args.frame_range[0]}_{args.frame_range[1]}.csv"
    )
    output_plot = args.output_dir / (
        f"temporal_depth_{args.frame_range[0]}_{args.frame_range[1]}.png"
    )
    write_depth_csv(observations, output_csv)
    write_depth_plot(observations, output_plot)
    print(f"CSV: {output_csv}")
    print(f"Plot: {output_plot}")


if __name__ == "__main__":
    main()
