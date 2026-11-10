"""Extract full-body canonical pose sequences from video using MediaPipe."""

from __future__ import annotations

from pathlib import Path

import cv2
import mediapipe as mp

from app.ml.pose.canonical import CanonicalPoseSequence
from app.ml.pose.mediapipe_adapter import mediapipe_landmarks_to_frame


MODEL_PATH = (
    Path(__file__).resolve().parents[3]
    / "models"
    / "pose_landmarker_full.task"
)


def extract_full_body_pose_sequence(
    video_path: str | Path,
) -> CanonicalPoseSequence:
    """
    Extract a canonical full-body pose sequence from a video.

    Each video frame produces one FramePoseObservation. Frames where
    MediaPipe does not detect a person are retained with missing keypoints.
    """
    video_path = Path(video_path)

    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"MediaPipe pose model not found: {MODEL_PATH}"
        )

    capture = cv2.VideoCapture(str(video_path))

    if not capture.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    fps = float(capture.get(cv2.CAP_PROP_FPS))

    if fps <= 0:
        capture.release()
        raise ValueError(f"Video has invalid FPS: {fps}")

    frames = []
    frame_index = 0

    try:
        BaseOptions = mp.tasks.BaseOptions
        PoseLandmarker = mp.tasks.vision.PoseLandmarker
        PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
        RunningMode = mp.tasks.vision.RunningMode

        options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(MODEL_PATH)),
            running_mode=RunningMode.VIDEO,
            num_poses=1,
        )

        with PoseLandmarker.create_from_options(options) as landmarker:
            while True:
                success, frame = capture.read()

                if not success:
                    break

                height_px, width_px = frame.shape[:2]

                # MediaPipe expects an RGB image.
                rgb_frame = cv2.cvtColor(
                    frame,
                    cv2.COLOR_BGR2RGB,
                )

                mp_image = mp.Image(
                    image_format=mp.ImageFormat.SRGB,
                    data=rgb_frame,
                )

                timestamp_ms = round(frame_index * 1000.0 / fps)

                detection = landmarker.detect_for_video(
                    mp_image,
                    timestamp_ms,
                )

                landmarks = (
                    detection.pose_landmarks[0]
                    if detection.pose_landmarks
                    else None
                )

                canonical_frame = mediapipe_landmarks_to_frame(
                    landmarks,
                    frame_index=frame_index,
                    timestamp_ms=timestamp_ms,
                    width_px=width_px,
                    height_px=height_px,
                    player_presence=(
                        "PLAYER_PRESENT"
                        if landmarks
                        else "PLAYER_ABSENT"
                    ),
                )

                frames.append(canonical_frame)
                frame_index += 1

    finally:
        capture.release()

    return CanonicalPoseSequence(
        frames=tuple(frames),
        estimator_name="MediaPipe PoseLandmarker",
        estimator_version=getattr(mp, "__version__", None),
        model_name=MODEL_PATH.name,
        fps=fps,
    )
