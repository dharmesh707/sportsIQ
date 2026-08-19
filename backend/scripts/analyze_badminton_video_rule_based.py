"""Rule-based badminton biomechanics analysis for a local video file."""

import math
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np


MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "pose_landmarker_full.task"
_LANDMARKS = {
    "left_shoulder": 11,
    "right_shoulder": 12,
    "right_elbow": 14,
    "right_wrist": 16,
    "left_hip": 23,
    "right_hip": 24,
    "right_knee": 26,
    "right_ankle": 28,
}
_TEMPLATES = {
    "viktor_axelsen": {"elbow_angle": 165, "shoulder_elevation": 25, "knee_angle": 160,
                       "hip_shoulder_separation": 35, "torso_inclination": 12},
    "kento_momota": {"elbow_angle": 160, "shoulder_elevation": 20, "knee_angle": 155,
                     "hip_shoulder_separation": 30, "torso_inclination": 10},
}


def _angle(first: np.ndarray, vertex: np.ndarray, last: np.ndarray) -> float:
    first_vector = first - vertex
    last_vector = last - vertex
    denominator = np.linalg.norm(first_vector) * np.linalg.norm(last_vector)
    if denominator == 0:
        return 0.0
    return math.degrees(math.acos(float(np.clip(np.dot(first_vector, last_vector) / denominator, -1, 1))))


def _point(landmarks, name: str) -> np.ndarray:
    landmark = landmarks[_LANDMARKS[name]]
    return np.array([landmark.x, landmark.y, landmark.z], dtype=float)


def _frame_angles(landmarks) -> dict[str, float]:
    left_shoulder = _point(landmarks, "left_shoulder")
    right_shoulder = _point(landmarks, "right_shoulder")
    right_hip = _point(landmarks, "right_hip")
    return {
        "elbow_angle": _angle(_point(landmarks, "right_shoulder"), _point(landmarks, "right_elbow"), _point(landmarks, "right_wrist")),
        "shoulder_elevation": abs(math.degrees(math.atan2(_point(landmarks, "right_wrist")[1] - right_shoulder[1], _point(landmarks, "right_wrist")[0] - right_shoulder[0]))),
        "knee_angle": _angle(_point(landmarks, "right_hip"), _point(landmarks, "right_knee"), _point(landmarks, "right_ankle")),
        "hip_shoulder_separation": abs(math.degrees(math.atan2(right_shoulder[2] - right_hip[2], right_shoulder[0] - right_hip[0]))),
        "torso_inclination": abs(math.degrees(math.atan2(right_shoulder[1] - right_hip[1], right_shoulder[0] - right_hip[0]))),
    }


def analyze(video_path: str | Path, template_name: str = "viktor_axelsen") -> dict:
    """Analyze a video and return JSON-serializable detector output."""
    if template_name not in _TEMPLATES:
        raise ValueError(f"Unknown template: {template_name}")
    if not MODEL_PATH.exists():
        raise FileNotFoundError("MediaPipe model not found: models/pose_landmarker_full.task")

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"Could not open video: {video_path}")
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    frame_count = 0
    poses = []
    wrist_y = []
    try:
        base_options = mp.tasks.BaseOptions(model_asset_path=str(MODEL_PATH))
        options = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_poses=1,
        )
        with mp.tasks.vision.PoseLandmarker.create_from_options(options) as landmarker:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                timestamp_ms = int(frame_count * 1000 / fps) if fps else frame_count
                image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                detection = landmarker.detect_for_video(image, timestamp_ms)
                frame_count += 1
                if detection.pose_landmarks:
                    landmarks = detection.pose_landmarks[0]
                    poses.append((frame_count - 1, landmarks))
                    wrist_y.append(float(landmarks[_LANDMARKS["right_wrist"]].y))
    finally:
        capture.release()

    detection_rate = len(poses) / frame_count if frame_count else 0.0
    if len(poses) < 5 or detection_rate < 0.3:
        raise ValueError(
            f"Insufficient pose detection: {len(poses)} detected frames out of {frame_count} "
            f"({detection_rate:.1%})"
        )

    velocity = np.abs(np.diff(wrist_y))
    contact_index = int(np.argmax(velocity) + 1) if len(velocity) else 0
    contact_frame, contact_landmarks = poses[contact_index]
    angles = {key: round(value, 1) for key, value in _frame_angles(contact_landmarks).items()}
    template = _TEMPLATES[template_name]
    differences = [abs(angles[key] - value) for key, value in template.items()]
    template_similarity = max(0.0, 100.0 - sum(differences) / len(differences) * 2.0)
    technique_score = max(0.0, min(100.0, template_similarity))
    wrist_peak = float(velocity.max()) if len(velocity) else 0.0
    if wrist_peak > 0.08 and angles["knee_angle"] < 150:
        shot_type = "JUMP_SMASH"
    elif wrist_peak > 0.08:
        shot_type = "STICK_SMASH"
    elif angles["shoulder_elevation"] > 45:
        shot_type = "FH_CLEAR"
    elif angles["elbow_angle"] < 120:
        shot_type = "FH_DROP"
    else:
        shot_type = "FH_DRIVE"
    return {
        "video": str(video_path), "fps": fps, "detected_frames": len(poses),
        "detection_rate": round(detection_rate, 4), "contact_frame": contact_frame,
        "shot_type": shot_type, "angles": angles, "technique_score": round(technique_score, 1),
        "template": template_name, "template_similarity": round(template_similarity, 1),
    }