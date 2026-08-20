"""
Real MediaPipe integration tests. NOTHING is mocked here.

These generate genuine MP4 files with OpenCV and push them through the real
detector - real decode, real PoseLandmarker inference, real error paths.

WHAT THESE DO AND DO NOT PROVE
------------------------------
They prove the pipeline is wired end to end and correctly REJECTS footage it
cannot analyze. They do NOT prove the success path, because a synthetic
video contains no human and MediaPipe will (correctly) find no pose in one.

Verifying the success path requires real footage of a real player. Run:

    python scripts/smoke_test.py /path/to/your/clip.mp4

There is deliberately no synthetic "athlete" here. Rendering a stick figure
until the pose model latched onto it would produce a green test that proves
nothing about real video, which is worse than an honest gap.
"""

import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

from scripts.analyze_badminton_video_rule_based import (
    InsufficientPoseError,
    MODEL_PATH,
    VideoError,
    analyze,
    probe_video,
)

pytestmark = pytest.mark.integration


def _write_video(path: Path, frames: int = 40, size: tuple[int, int] = (320, 240),
                 noise: bool = True) -> Path:
    width, height = size
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 30.0, (width, height))
    rng = np.random.default_rng(1234)
    for _ in range(frames):
        frame = (
            rng.integers(0, 255, (height, width, 3), dtype=np.uint8)
            if noise
            else np.zeros((height, width, 3), dtype=np.uint8)
        )
        writer.write(frame)
    writer.release()
    return path


def test_model_file_is_present():
    assert MODEL_PATH.exists(), (
        "models/pose_landmarker_full.task is missing - the production detector "
        "cannot run without it."
    )


def test_probe_reads_real_video_metadata(tmp_path):
    video = _write_video(tmp_path / "clip.mp4", frames=40, size=(320, 240))
    probe = probe_video(video)
    assert probe["width"] == 320
    assert probe["height"] == 240
    assert probe["fps"] == pytest.approx(30.0, abs=0.5)


def test_probe_rejects_a_nonexistent_file(tmp_path):
    with pytest.raises(VideoError):
        probe_video(tmp_path / "does-not-exist.mp4")


def test_probe_rejects_a_corrupt_file(tmp_path):
    corrupt = tmp_path / "corrupt.mp4"
    corrupt.write_bytes(b"this is definitely not an mp4 container")
    with pytest.raises(VideoError):
        probe_video(corrupt)


def test_probe_rejects_undersized_video(tmp_path):
    tiny = _write_video(tmp_path / "tiny.mp4", frames=20, size=(64, 48))
    with pytest.raises(VideoError, match="too small"):
        probe_video(tiny)


def test_real_mediapipe_run_rejects_footage_with_no_athlete(tmp_path):
    """
    THE REAL END-TO-END INFERENCE TEST.

    Decodes a genuine MP4 and runs genuine PoseLandmarker inference over
    every frame. No human is present, so detection rate is ~0 and the
    detector must raise InsufficientPoseError rather than returning a
    confident score derived from nothing.
    """
    video = _write_video(tmp_path / "noise.mp4", frames=40, size=(320, 240))
    with pytest.raises(InsufficientPoseError) as exc:
        analyze(video)
    assert "Insufficient pose detection" in str(exc.value)


def test_real_mediapipe_run_on_blank_footage_also_rejects(tmp_path):
    video = _write_video(tmp_path / "blank.mp4", frames=30, size=(320, 240), noise=False)
    with pytest.raises(InsufficientPoseError):
        analyze(video)


def test_detector_cli_returns_nonzero_and_json_error(tmp_path):
    """The CLI must fail cleanly with JSON, not a raw traceback."""
    corrupt = tmp_path / "corrupt.mp4"
    corrupt.write_bytes(b"nope")
    backend_root = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [sys.executable, "scripts/analyze_badminton_video_rule_based.py", str(corrupt)],
        cwd=backend_root,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 1
    assert '"error"' in proc.stdout
    assert "Traceback" not in proc.stdout
