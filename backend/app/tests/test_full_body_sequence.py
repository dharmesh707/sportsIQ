
from types import SimpleNamespace

import numpy as np
import pytest

from app.ml.pose import full_body_sequence as extractor
from app.ml.pose.canonical import (
    CANONICAL_KEYPOINT_NAMES,
    CanonicalPoseSequence,
)


class FakeCapture:
    def __init__(self, frames, fps=30.0, opened=True):
        self.frames = list(frames)
        self.fps = fps
        self.opened = opened
        self.released = False

    def isOpened(self):
        return self.opened

    def get(self, property_id):
        if property_id == extractor.cv2.CAP_PROP_FPS:
            return self.fps
        return 0

    def read(self):
        if not self.frames:
            return False, None
        return True, self.frames.pop(0)

    def release(self):
        self.released = True


class FakeLandmarker:
    def __init__(self, detections):
        self.detections = list(detections)
        self.timestamps = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def detect_for_video(self, image, timestamp_ms):
        self.timestamps.append(timestamp_ms)
        return self.detections.pop(0)


def make_landmarks():
    return [
        SimpleNamespace(
            x=index / 100,
            y=index / 200,
            z=-index / 1000,
            visibility=0.9,
            presence=0.8,
        )
        for index in range(33)
    ]


def make_detection(landmarks=None):
    if landmarks is None:
        return SimpleNamespace(pose_landmarks=[])

    return SimpleNamespace(pose_landmarks=[landmarks])


def configure_mediapipe(monkeypatch, landmarker):
    fake_options = SimpleNamespace(
        base_options=None,
        running_mode=None,
        num_poses=None,
    )

    fake_pose_landmarker = SimpleNamespace(
        create_from_options=lambda options: landmarker
    )

    fake_tasks = SimpleNamespace(
        BaseOptions=lambda **kwargs: SimpleNamespace(**kwargs),
        vision=SimpleNamespace(
            PoseLandmarker=fake_pose_landmarker,
            PoseLandmarkerOptions=lambda **kwargs: fake_options,
            RunningMode=SimpleNamespace(VIDEO="VIDEO"),
        ),
    )

    fake_mp = SimpleNamespace(
        tasks=fake_tasks,
        Image=lambda **kwargs: SimpleNamespace(**kwargs),
        ImageFormat=SimpleNamespace(SRGB="SRGB"),
        __version__="test-version",
    )

    monkeypatch.setattr(extractor, "mp", fake_mp)

    monkeypatch.setattr(
        extractor.cv2,
        "cvtColor",
        lambda frame, code: frame,
    )


def test_extract_full_body_sequence(monkeypatch, tmp_path):
    video_path = tmp_path / "sample.mp4"
    video_path.touch()

    frames = [
        np.zeros((1080, 608, 3), dtype=np.uint8),
        np.zeros((1080, 608, 3), dtype=np.uint8),
    ]

    capture = FakeCapture(frames, fps=30.0)

    monkeypatch.setattr(
        extractor.cv2,
        "VideoCapture",
        lambda path: capture,
    )

    monkeypatch.setattr(
        extractor,
        "MODEL_PATH",
        tmp_path / "pose_landmarker_full.task",
    )
    extractor.MODEL_PATH.touch()

    landmarker = FakeLandmarker(
        [
            make_detection(make_landmarks()),
            make_detection(),
        ]
    )

    configure_mediapipe(monkeypatch, landmarker)

    sequence = extractor.extract_full_body_pose_sequence(video_path)

    assert isinstance(sequence, CanonicalPoseSequence)
    assert len(sequence.frames) == 2
    assert sequence.fps == 30.0

    first_frame = sequence.frames[0]
    second_frame = sequence.frames[1]

    assert first_frame.frame_index == 0
    assert second_frame.frame_index == 1

    assert first_frame.timestamp_ms == 0
    assert second_frame.timestamp_ms == 33

    assert first_frame.width_px == 608
    assert first_frame.height_px == 1080

    assert first_frame.player_presence == "PLAYER_PRESENT"
    assert second_frame.player_presence == "PLAYER_ABSENT"

    assert set(first_frame.keypoints) == set(CANONICAL_KEYPOINT_NAMES)

    assert first_frame.keypoints["left_shoulder"].present
    assert first_frame.keypoints["left_shoulder"].x_norm == pytest.approx(0.11)

    assert not second_frame.keypoints["left_shoulder"].present

    assert sequence.estimator_name == "MediaPipe PoseLandmarker"
    assert sequence.model_name == extractor.MODEL_PATH.name

    assert capture.released


def test_missing_video_raises_file_not_found(tmp_path):
    missing_path = tmp_path / "missing.mp4"

    with pytest.raises(FileNotFoundError):
        extractor.extract_full_body_pose_sequence(missing_path)


def test_video_that_cannot_be_opened_raises(monkeypatch, tmp_path):
    video_path = tmp_path / "sample.mp4"
    video_path.touch()

    capture = FakeCapture([], opened=False)

    monkeypatch.setattr(
        extractor.cv2,
        "VideoCapture",
        lambda path: capture,
    )

    with pytest.raises(RuntimeError, match="Could not open video"):
        extractor.extract_full_body_pose_sequence(video_path)


def test_invalid_fps_raises_and_releases_capture(
    monkeypatch,
    tmp_path,
):
    video_path = tmp_path / "sample.mp4"
    video_path.touch()

    capture = FakeCapture([], fps=0.0)

    monkeypatch.setattr(
        extractor.cv2,
        "VideoCapture",
        lambda path: capture,
    )

    with pytest.raises(ValueError, match="invalid FPS"):
        extractor.extract_full_body_pose_sequence(video_path)

    assert capture.released


def test_missing_model_raises(monkeypatch, tmp_path):
    video_path = tmp_path / "sample.mp4"
    video_path.touch()

    missing_model = tmp_path / "missing.task"

    monkeypatch.setattr(
        extractor,
        "MODEL_PATH",
        missing_model,
    )

    with pytest.raises(FileNotFoundError, match="model not found"):
        extractor.extract_full_body_pose_sequence(video_path)
