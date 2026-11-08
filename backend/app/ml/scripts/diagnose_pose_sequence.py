"""Interactive offline visual diagnostics for a saved badminton pose sequence."""

from __future__ import annotations

import argparse
import csv
import math
from bisect import bisect_left
from dataclasses import dataclass
from pathlib import Path

import cv2

from app.ml.pose.sequence import PoseFrame, PoseSequence, extract_pose_sequence
from app.ml.pose.presence import (
    load_presence_review,
    present_intervals,
)

ANGLE_THRESHOLD_DEGREES = 30.0
LANDMARKS = (
    ("shoulder", "shoulder"),
    ("elbow", "elbow"),
    ("wrist", "wrist"),
)
CONNECTIONS = (("shoulder", "elbow"), ("elbow", "wrist"))


@dataclass(frozen=True)
class CsvObservation:
    frame_index: int
    timestamp_ms: int
    left_angle: float | None
    right_angle: float | None
    left_angle_2d: float | None
    right_angle_2d: float | None
    visibilities: dict[str, float | None]
    presences: dict[str, float | None]
    right_disagreement: float | None = None
    right_disagreement_warning: bool = False
    racket_arm_quality_status: str = "unknown"
    racket_arm_quality_reasons: str = ""


@dataclass(frozen=True)
class SynchronizedObservation:
    csv: CsvObservation
    pose_frame: PoseFrame
    timestamp_delta_ms: int


@dataclass(frozen=True)
class AngleJump:
    side: str
    previous_frame_index: int
    frame_index: int
    previous_timestamp_ms: int
    timestamp_ms: int
    change_degrees: float


def _optional_float(value: str) -> float | None:
    if value.strip() == "":
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def load_csv_observations(csv_path: Path) -> list[CsvObservation]:
    """Load CSV observations while retaining blank/invalid measurements as None."""
    observations: list[CsvObservation] = []
    with csv_path.open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            observations.append(CsvObservation(
                frame_index=int(row["frame_index"]),
                timestamp_ms=int(row["timestamp_ms"]),
                left_angle=_optional_float(row["left_elbow_angle_degrees"]),
                right_angle=_optional_float(row["right_elbow_angle_degrees"]),
                left_angle_2d=_optional_float(row.get("left_elbow_angle_2d_degrees", "")),
                right_angle_2d=_optional_float(row.get("right_elbow_angle_2d_degrees", "")),
                visibilities={
                    key: _optional_float(row.get(key, ""))
                    for key in (
                        "left_shoulder_visibility",
                        "left_elbow_visibility",
                        "left_wrist_visibility",
                        "right_shoulder_visibility",
                        "right_elbow_visibility",
                        "right_wrist_visibility",
                    )
                },
                presences={
                    key: _optional_float(row.get(key, ""))
                    for key in (
                        "left_shoulder_presence",
                        "left_elbow_presence",
                        "left_wrist_presence",
                        "right_shoulder_presence",
                        "right_elbow_presence",
                        "right_wrist_presence",
                    )
                },
                right_disagreement=_optional_float(
                    row.get("right_elbow_angle_disagreement_degrees", "")
                ),
                right_disagreement_warning=row.get(
                    "right_elbow_angle_disagreement_warning", ""
                ).strip().lower() == "true",
                racket_arm_quality_status=row.get(
                    "racket_arm_quality_status", "unknown"
                ),
                racket_arm_quality_reasons=row.get(
                    "racket_arm_quality_reasons", ""
                ),
            ))
    return observations


def synchronize_observations(
    sequence: PoseSequence,
    observations: list[CsvObservation],
    tolerance_ms: int = 2,
) -> list[SynchronizedObservation]:
    """Match CSV rows to extracted frames by nearest timestamp."""
    frames = sequence.frames
    timestamps = [frame.timestamp_ms for frame in frames]
    synchronized: list[SynchronizedObservation] = []
    for observation in observations:
        position = bisect_left(timestamps, observation.timestamp_ms)
        candidates = []
        if position < len(frames):
            candidates.append(frames[position])
        if position > 0:
            candidates.append(frames[position - 1])
        if not candidates:
            continue
        pose_frame = min(
            candidates,
            key=lambda frame: abs(frame.timestamp_ms - observation.timestamp_ms),
        )
        delta = abs(pose_frame.timestamp_ms - observation.timestamp_ms)
        if delta <= tolerance_ms:
            synchronized.append(SynchronizedObservation(observation, pose_frame, delta))
    return synchronized


def detect_angle_jumps(
    observations: list[CsvObservation],
    threshold_degrees: float = ANGLE_THRESHOLD_DEGREES,
) -> list[AngleJump]:
    """Find jumps between consecutive valid observations; missing values break runs."""
    jumps: list[AngleJump] = []
    previous: dict[str, CsvObservation | None] = {"left": None, "right": None}
    for observation in observations:
        for side, attribute in (("left", "left_angle"), ("right", "right_angle")):
            value = getattr(observation, attribute)
            prior = previous[side]
            if value is None:
                previous[side] = None
                continue
            if prior is not None:
                prior_value = getattr(prior, attribute)
                change = abs(value - prior_value)
                if change > threshold_degrees:
                    jumps.append(AngleJump(
                        side=side,
                        previous_frame_index=prior.frame_index,
                        frame_index=observation.frame_index,
                        previous_timestamp_ms=prior.timestamp_ms,
                        timestamp_ms=observation.timestamp_ms,
                        change_degrees=change,
                    ))
            previous[side] = observation
    return jumps


def select_frame_indices(
    synchronized: list[SynchronizedObservation],
    frame_indices: list[int],
) -> list[SynchronizedObservation]:
    """Return synchronized observations for requested source frame indices."""
    requested = set(frame_indices)
    return [
        observation
        for observation in synchronized
        if observation.pose_frame.frame_index in requested
    ]


def _draw_arm(
    frame,
    arm,
    color: tuple[int, int, int],
    radius: int = 5,
    thickness: int = 2,
) -> None:
    points = {}
    for name, _ in LANDMARKS:
        landmark = getattr(arm, name)
        if landmark.present and landmark.x is not None and landmark.y is not None:
            point = (round(landmark.x * frame.shape[1]), round(landmark.y * frame.shape[0]))
            points[name] = point
            cv2.circle(frame, point, radius, color, -1)
    for start, end in CONNECTIONS:
        if start in points and end in points:
            cv2.line(frame, points[start], points[end], color, thickness)


def render_diagnostic_frame(
    image,
    observation: SynchronizedObservation,
    suspicious: bool,
):
    """Render bilateral landmarks and scalar diagnostics onto a video frame."""
    frame = image.copy()
    _draw_arm(frame, observation.pose_frame.left, (150, 100, 0), 4, 2)
    _draw_arm(frame, observation.pose_frame.right, (0, 220, 255), 7, 4)
    csv_row = observation.csv
    status = "ANGLE JUMP" if suspicious else "normal"
    lines = [
        f"frame {csv_row.frame_index}  timestamp {csv_row.timestamp_ms} ms  ({status})",
        f"L angle 2D/3D: {_format_value(csv_row.left_angle_2d)} / "
        f"{_format_value(csv_row.left_angle)}   "
        f"R angle 2D/3D: {_format_value(csv_row.right_angle_2d)} / "
        f"{_format_value(csv_row.right_angle)}",
        f"R disagreement: {_format_value(csv_row.right_disagreement)}  "
        f"Racket quality: {csv_row.racket_arm_quality_status}",
        "L vis: " + _confidence_text(csv_row, "left"),
        "R vis: " + _confidence_text(csv_row, "right"),
    ]
    for index, line in enumerate(lines):
        cv2.putText(
            frame,
            line,
            (12, 28 + index * 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 0, 255) if suspicious and index == 0 else (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
    if suspicious:
        cv2.rectangle(frame, (0, 0), (frame.shape[1] - 1, frame.shape[0] - 1), (0, 0, 255), 5)
    return frame


def _format_value(value: float | None) -> str:
    return "missing" if value is None else f"{value:.1f}"


def _confidence_text(observation: CsvObservation, side: str) -> str:
    return " ".join(
        f"{joint[0].upper()}:{_format_value(observation.visibilities[f'{side}_{joint}_visibility'])}/"
        f"{_format_value(observation.presences[f'{side}_{joint}_presence'])}"
        for joint, _ in LANDMARKS
    )


def run_diagnostic(
    video_path: Path,
    csv_path: Path,
    output_dir: Path,
    tolerance_ms: int = 2,
    frame_indices: list[int] | None = None,
) -> None:
    sequence = extract_pose_sequence(video_path)
    observations = load_csv_observations(csv_path)
    synchronized = synchronize_observations(sequence, observations, tolerance_ms)
    if not synchronized:
        raise ValueError("No CSV observations could be synchronized to video timestamps.")
    if frame_indices is not None:
        synchronized = select_frame_indices(synchronized, frame_indices)
        if not synchronized:
            raise ValueError("None of the requested frame indices were found in the CSV.")
    jumps = detect_angle_jumps(observations)
    suspicious_frames = {
        frame_index
        for jump in jumps
        for frame_index in (jump.previous_frame_index, jump.frame_index)
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    by_frame = {item.pose_frame.frame_index: item for item in synchronized}
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"Could not open video: {video_path}")
    current = 0
    ordered_frames = list(by_frame)
    try:
        while ordered_frames:
            current = max(0, min(current, len(ordered_frames) - 1))
            frame_index = ordered_frames[current]
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ok, image = capture.read()
            if not ok:
                raise ValueError(f"Could not read video frame {frame_index}.")
            item = by_frame[frame_index]
            display = render_diagnostic_frame(
                image,
                item,
                item.csv.frame_index in suspicious_frames,
            )
            cv2.imshow("SportsIQ pose diagnostic", display)
            key = cv2.waitKey(0) & 0xFF
            if key in (ord("q"), 27):
                break
            if key in (ord("n"), ord("d"), 83):
                current += 1
            elif key in (ord("p"), ord("a"), 81):
                current -= 1
            elif key == ord("e"):
                path = output_dir / f"diagnostic_frame_{frame_index:06d}.png"
                cv2.imwrite(str(path), display)
                print(f"Exported: {path}")
            elif key == ord("s"):
                current = next(
                    (index for index, value in enumerate(ordered_frames[current + 1:], current + 1)
                     if value in suspicious_frames),
                    len(ordered_frames),
                )
            if current >= len(ordered_frames):
                break
    finally:
        capture.release()
        cv2.destroyAllWindows()
    print(f"Synchronized observations: {len(synchronized)}")
    print(f"Angle jumps: {len(jumps)}")


def export_diagnostic_frames(
    video_path: Path,
    csv_path: Path,
    output_dir: Path,
    frame_indices: list[int],
    tolerance_ms: int = 2,
) -> list[Path]:
    """Export annotated PNGs for selected frames without opening a GUI."""
    sequence = extract_pose_sequence(video_path)
    observations = load_csv_observations(csv_path)
    synchronized = synchronize_observations(sequence, observations, tolerance_ms)
    selected = select_frame_indices(synchronized, frame_indices)
    if not selected:
        raise ValueError("None of the requested frame indices were found in the CSV.")
    suspicious_frames = {
        item.csv.frame_index
        for item in selected
        if item.csv.right_disagreement_warning
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"Could not open video: {video_path}")
    paths: list[Path] = []
    try:
        for item in selected:
            frame_index = item.pose_frame.frame_index
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ok, image = capture.read()
            if not ok:
                raise ValueError(f"Could not read video frame {frame_index}.")
            rendered = render_diagnostic_frame(
                image,
                item,
                frame_index in suspicious_frames,
            )
            path = output_dir / f"diagnostic_frame_{frame_index:06d}.png"
            if not cv2.imwrite(str(path), rendered):
                raise ValueError(f"Could not write diagnostic frame: {path}")
            paths.append(path)
    finally:
        capture.release()
    return paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Review pose landmarks against a video.")
    parser.add_argument("video", type=Path, help="Original video path.")
    parser.add_argument("csv", type=Path, help="Pose-sequence CSV path.")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tolerance-ms", type=int, default=2)
    parser.add_argument(
        "--presence-review",
        type=Path,
        help=(
            "CSV with frame_index,player_presence,notes for reviewed "
            "PLAYER_PRESENT/PLAYER_ABSENT/UNCERTAIN statuses."
        ),
    )
    parser.add_argument(
        "--presence-summary",
        action="store_true",
        help="Print contiguous reviewed PLAYER_PRESENT intervals and exit.",
    )
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--frames", type=int, nargs="+")
    selection.add_argument(
        "--frame-range",
        type=int,
        nargs=2,
        metavar=("START", "END"),
        help="Inclusive frame range for diagnostic export.",
    )
    parser.add_argument(
        "--export-frames",
        action="store_true",
        help="Export selected frames as PNGs instead of opening the interactive viewer.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.presence_summary and args.presence_review is None:
        parser.error("--presence-summary requires --presence-review")
    if args.presence_summary:
        try:
            reviewed_presence = load_presence_review(args.presence_review)
        except (OSError, ValueError) as error:
            raise SystemExit(str(error)) from error
        frame_indices = [
            observation.frame_index
            for observation in load_csv_observations(args.csv)
        ]
        intervals = present_intervals(frame_indices, reviewed_presence)
        for interval in intervals:
            print(f"{interval.start_frame},{interval.end_frame}")
        return
    if args.frame_range is not None:
        start, end = args.frame_range
        if start > end:
            parser.error("frame-range START must be less than or equal to END")
        frame_indices = list(range(start, end + 1))
    else:
        frame_indices = args.frames or [33, 46, 47, 48, 135, 136, 137]
    if args.export_frames:
        paths = export_diagnostic_frames(
            args.video,
            args.csv,
            args.output_dir,
            frame_indices,
            args.tolerance_ms,
        )
        print(f"Exported {len(paths)} diagnostic frames to {args.output_dir}")
    else:
        run_diagnostic(
            args.video,
            args.csv,
            args.output_dir,
            args.tolerance_ms,
            frame_indices,
        )


if __name__ == "__main__":
    main()
