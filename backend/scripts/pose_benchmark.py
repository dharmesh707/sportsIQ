"""Offline pose-estimator benchmark with a shared decoded-frame representation.

This module measures runtime and keypoint completeness only. It does not
measure pose accuracy and is intentionally separate from the API pipeline.
"""

from __future__ import annotations

import argparse
import importlib
import json
import math
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import cv2
import numpy as np

COMMON_JOINTS = (
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
)
MEDIAPIPE_INDICES = {
    name: index for name, index in zip(COMMON_JOINTS, (11, 12, 13, 14, 15, 16))
}
COCO_INDICES = {
    name: index for name, index in zip(COMMON_JOINTS, (5, 6, 7, 8, 9, 10))
}


@dataclass(frozen=True)
class DecodedFrame:
    frame_index: int
    timestamp_ms: int
    image: np.ndarray


@dataclass(frozen=True)
class Keypoint:
    x: float | None
    y: float | None
    z: float | None
    confidence: float | None
    source_x: float | None = None
    source_y: float | None = None

    @property
    def available(self) -> bool:
        return self.x is not None and self.y is not None


@dataclass(frozen=True)
class FrameResult:
    frame_index: int
    timestamp_ms: int
    inference_ms: float | None
    detected: bool
    keypoints: dict[str, Keypoint]
    error: str | None = None


@dataclass(frozen=True)
class VideoInfo:
    width: int
    height: int
    fps: float
    frame_count: int
    duration_seconds: float


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _confidence(value: Any) -> float | None:
    number = _finite(value)
    return number if number is not None and 0.0 <= number <= 1.0 else None


def _empty_keypoints() -> dict[str, Keypoint]:
    return {name: Keypoint(None, None, None, None) for name in COMMON_JOINTS}


def _timestamp_ms(frame_index: int, fps: float, previous: int | None) -> int:
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError(f"Video FPS must be finite and positive; got {fps!r}")
    timestamp = round(frame_index * 1000 / fps)
    return max(timestamp, previous + 1 if previous is not None else 0)


def decode_video(video_path: Path) -> tuple[VideoInfo, list[DecodedFrame]]:
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"Could not open video: {video_path}")
    try:
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        if not math.isfinite(fps) or fps <= 0:
            raise ValueError(f"Video FPS must be finite and positive; got {fps!r}")
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frames: list[DecodedFrame] = []
        previous: int | None = None
        while True:
            ok, image = capture.read()
            if not ok:
                break
            index = len(frames)
            timestamp = _timestamp_ms(index, fps, previous)
            previous = timestamp
            frames.append(DecodedFrame(index, timestamp, image))
        info = VideoInfo(width, height, fps, len(frames), len(frames) / fps)
        return info, frames
    finally:
        capture.release()


def _from_points(
    points: Any,
    scores: Any,
    mapping: dict[str, int],
    coordinate_system: str,
    frame_width: int,
    frame_height: int,
) -> dict[str, Keypoint]:
    """Convert estimator points to canonical normalized image coordinates.

    ``z`` remains estimator-native and is never treated as a shared metric.
    """
    if coordinate_system not in {"normalized_image", "pixel_image"}:
        raise ValueError(f"Unsupported coordinate system: {coordinate_system}")
    if frame_width <= 0 or frame_height <= 0:
        raise ValueError("Frame dimensions must be positive")
    result = _empty_keypoints()
    if points is None:
        return result
    points_array = np.asarray(points)
    scores_array = None if scores is None else np.asarray(scores)
    if points_array.ndim == 3:
        points_array = points_array[0]
    if scores_array is not None and scores_array.ndim > 1:
        scores_array = scores_array[0]
    for name, index in mapping.items():
        if index >= len(points_array):
            continue
        point = points_array[index]
        if len(point) < 2:
            continue
        source_x, source_y = _finite(point[0]), _finite(point[1])
        if source_x is None or source_y is None:
            continue
        if coordinate_system == "normalized_image":
            x, y = source_x, source_y
        else:
            x, y = source_x / frame_width, source_y / frame_height
        z = _finite(point[2]) if len(point) > 2 else None
        score = _confidence(scores_array[index]) if scores_array is not None and index < len(scores_array) else None
        result[name] = Keypoint(x, y, z, score, source_x, source_y)
    return result


def _mediapipe_backend(model_path: Path):
    mp = importlib.import_module("mediapipe")
    if not model_path.exists():
        raise FileNotFoundError(f"MediaPipe model not found: {model_path}")
    base = mp.tasks.BaseOptions(model_asset_path=str(model_path))
    options = mp.tasks.vision.PoseLandmarkerOptions(
        base_options=base,
        running_mode=mp.tasks.vision.RunningMode.VIDEO,
        num_poses=1,
    )
    landmarker = mp.tasks.vision.PoseLandmarker.create_from_options(options)

    def infer(frame: DecodedFrame) -> dict[str, Keypoint]:
        rgb = cv2.cvtColor(frame.image, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        detection = landmarker.detect_for_video(image, frame.timestamp_ms)
        if not detection.pose_landmarks:
            return _empty_keypoints()
        landmarks = detection.pose_landmarks[0]
        points = [(item.x, item.y, item.z) for item in landmarks]
        scores = [getattr(item, "visibility", None) for item in landmarks]
        return _from_points(
            points, scores, MEDIAPIPE_INDICES, "normalized_image",
            frame.image.shape[1], frame.image.shape[0],
        )

    return landmarker, infer


def _yolo_backend(model_path: Path):
    if not model_path.exists():
        raise FileNotFoundError(
            f"YOLO model is not available locally: {model_path}. "
            "Pass --yolo-model with an existing pose model; no download is performed."
        )
    module = importlib.import_module("ultralytics")
    model = module.YOLO(str(model_path), task="pose", verbose=False)

    def infer(frame: DecodedFrame) -> dict[str, Keypoint]:
        results = model.predict(frame.image, verbose=False)
        if not results or results[0].keypoints is None or len(results[0].keypoints.xy) == 0:
            return _empty_keypoints()
        keypoints = results[0].keypoints
        points = keypoints.xy[0].cpu().numpy()
        scores = keypoints.conf[0].cpu().numpy() if keypoints.conf is not None else None
        return _from_points(
            points, scores, COCO_INDICES, "pixel_image",
            frame.image.shape[1], frame.image.shape[0],
        )

    return model, infer


def _rtmpose_backend(model_path: Path):
    if not model_path.exists():
        raise FileNotFoundError(
            f"RTMPose configuration/model path is not available locally: {model_path}. "
            "No model download is performed."
        )
    module = importlib.import_module("rtmlib")
    body = module.Body(pose=str(model_path), device="cpu")

    def infer(frame: DecodedFrame) -> dict[str, Keypoint]:
        points, scores = body(frame.image)
        return _from_points(
            points, scores, COCO_INDICES, "pixel_image",
            frame.image.shape[1], frame.image.shape[0],
        )

    return body, infer


def _version(name: str) -> str | None:
    try:
        module = importlib.import_module(name)
    except ImportError:
        return None
    return getattr(module, "__version__", "unknown")


def _ranges(indices: Iterable[int]) -> list[list[int]]:
    ordered = sorted(set(indices))
    if not ordered:
        return []
    ranges: list[list[int]] = []
    start = previous = ordered[0]
    for index in ordered[1:]:
        if index != previous + 1:
            ranges.append([start, previous])
            start = index
        previous = index
    ranges.append([start, previous])
    return ranges


def _result_summary(results: list[FrameResult]) -> dict[str, Any]:
    latencies = [result.inference_ms for result in results if result.inference_ms is not None]
    missing = [result.frame_index for result in results if not result.detected]
    availability = {
        name: sum(result.keypoints[name].available for result in results)
        for name in COMMON_JOINTS
    }
    jitter: dict[str, float | None] = {}
    for name in COMMON_JOINTS:
        values = [
            result.keypoints[name].x
            for result in results
            if result.keypoints[name].x is not None
        ]
        jitter[name] = (
            statistics.mean(abs(b - a) for a, b in zip(values, values[1:]))
            if len(values) > 1 else None
        )
    return {
        "frames_processed": len(results),
        "detected_frames": sum(result.detected for result in results),
        "missing_detection_ranges": _ranges(missing),
        "valid_keypoints": availability,
        "latency_ms": {
            "count": len(latencies),
            "mean": statistics.mean(latencies) if latencies else None,
            "median": statistics.median(latencies) if latencies else None,
            "min": min(latencies) if latencies else None,
            "max": max(latencies) if latencies else None,
            "effective_fps": 1000.0 / statistics.mean(latencies) if latencies and statistics.mean(latencies) > 0 else None,
        },
        "temporal_jitter_mean_abs_x": jitter,
        "errors": [result.error for result in results if result.error],
    }


def _draw_overlay(image: np.ndarray, result: FrameResult, estimator: str) -> np.ndarray:
    output = image.copy()
    for point in result.keypoints.values():
        if point.available:
            cv2.circle(
                output,
                (round(point.x * output.shape[1]), round(point.y * output.shape[0])),
                4,
                (0, 220, 255),
                -1,
            )
    cv2.putText(output, f"{estimator} frame={result.frame_index}", (10, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    return output


def benchmark_estimator(
    estimator: str,
    frames: list[DecodedFrame],
    model_path: Path,
    output_dir: Path,
    *,
    yolo_model: Path | None = None,
    rtmpose_model: Path | None = None,
    overlay: bool = True,
    video_fps: float = 25.0,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        if estimator == "mediapipe":
            resource, infer = _mediapipe_backend(model_path)
            package = "mediapipe"
        elif estimator == "yolo":
            resource, infer = _yolo_backend(yolo_model or Path("yolo11n-pose.pt"))
            package = "ultralytics"
        elif estimator == "rtmpose":
            resource, infer = _rtmpose_backend(rtmpose_model or Path("rtmpose.onnx"))
            package = "rtmlib"
        else:
            raise ValueError(f"Unsupported estimator: {estimator}")
    except (ImportError, OSError, RuntimeError, ValueError) as error:
        return {
            "estimator": estimator,
            "status": "unavailable",
            "reason": f"{type(error).__name__}: {error}",
            "package_version": _version({"mediapipe": "mediapipe", "yolo": "ultralytics", "rtmpose": "rtmlib"}[estimator]),
        }

    results: list[FrameResult] = []
    writer = None
    processing_started = time.perf_counter()
    try:
        if overlay and frames:
            path = output_dir / f"{estimator}_overlay.mp4"
            writer = cv2.VideoWriter(
                str(path), cv2.VideoWriter_fourcc(*"mp4v"), video_fps,
                (frames[0].image.shape[1], frames[0].image.shape[0]),
            )
        for frame in frames:
            started = time.perf_counter()
            error = None
            try:
                keypoints = infer(frame)
            except Exception as exc:
                keypoints = _empty_keypoints()
                error = f"{type(exc).__name__}: {exc}"
            elapsed = (time.perf_counter() - started) * 1000.0
            result = FrameResult(
                frame.frame_index, frame.timestamp_ms, elapsed,
                any(point.available for point in keypoints.values()), keypoints, error,
            )
            results.append(result)
            if writer is not None:
                writer.write(_draw_overlay(frame.image, result, estimator))
    finally:
        if writer is not None:
            writer.release()
        close = getattr(resource, "close", None)
        if close is not None:
            close()
    summary = _result_summary(results)
    summary["processing_duration_seconds"] = time.perf_counter() - processing_started
    frame_path = output_dir / f"{estimator}_frames.jsonl"
    with frame_path.open("w", encoding="utf-8") as file:
        for result in results:
            file.write(json.dumps({
                "frame_index": result.frame_index,
                "timestamp_ms": result.timestamp_ms,
                "inference_ms": result.inference_ms,
                "detected": result.detected,
                "keypoints": {name: point.__dict__ for name, point in result.keypoints.items()},
                "error": result.error,
            }) + "\n")
    return {
        "estimator": estimator,
        "status": "completed",
        "package": package,
        "package_version": _version(package),
        "common_joints": list(COMMON_JOINTS),
        "configuration": {"model_path": str(model_path) if estimator == "mediapipe" else None},
        "coordinate_convention": {
            "x": "x_norm = x_px / frame_width",
            "y": "y_norm = y_px / frame_height",
            "canonical_units": "normalized_image",
            "source_coordinate_system": (
                "normalized_image" if estimator == "mediapipe" else "pixel_image"
            ),
            "source_values_preserved": ["source_x", "source_y"],
            "z": "estimator_native; not comparable across estimators",
            "frame_dimensions": {
                "width": frames[0].image.shape[1] if frames else None,
                "height": frames[0].image.shape[0] if frames else None,
            },
        },
        "summary": summary,
        "output_files": {
            "frames": str(frame_path),
            "overlay": str(output_dir / f"{estimator}_overlay.mp4") if writer is not None else None,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--estimators", nargs="+", choices=("mediapipe", "yolo", "rtmpose"),
                        default=["mediapipe"])
    parser.add_argument("--out-dir", type=Path, default=Path("data/benchmark/pose"))
    parser.add_argument("--model", type=Path, default=Path("models/pose_landmarker_full.task"))
    parser.add_argument("--yolo-model", type=Path)
    parser.add_argument("--rtmpose-model", type=Path)
    parser.add_argument("--no-overlay", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    info, frames = decode_video(args.video)
    reports = [
        benchmark_estimator(
            estimator, frames, args.model, args.out_dir,
            yolo_model=args.yolo_model, rtmpose_model=args.rtmpose_model,
            overlay=not args.no_overlay, video_fps=info.fps,
        )
        for estimator in args.estimators
    ]
    report = {
        "accuracy_note": "No landmark accuracy is reported; manually annotated ground truth is required.",
        "video": str(args.video),
        "video_info": info.__dict__,
        "frame_index_convention": "original zero-based decoded frame index",
        "estimators": reports,
    }
    report_path = args.out_dir / "benchmark_report.json"
    args.out_dir.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
