"""
Proves ml_pipeline.py's auto-detect mechanism actually works, not just that
it fails-safe to mock data. Uses a throwaway fake sport module rather than
a real one, so this test doesn't depend on any teammate's actual classifier
landing - it tests the plumbing, not the ML.
"""
import sys
import types

from app.ml_pipeline import run_pipeline
from app.schemas.analysis import AnalysisResult
from app.schemas.common import SportType


def test_pipeline_falls_back_to_mock_when_no_classifier_exists():
    result = run_pipeline(b"fake video bytes", SportType.ARCHERY)
    assert isinstance(result, AnalysisResult)
    assert result.sport_type == SportType.ARCHERY


def test_pipeline_routes_to_real_classifier_when_present(monkeypatch):
    fake_module = types.ModuleType("ml.sports.archery.classifier")

    def fake_analyze(video_bytes: bytes) -> AnalysisResult:
        from datetime import datetime, timezone
        return AnalysisResult(
            analysis_id="real-model-ran",
            sport_type=SportType.ARCHERY,
            action_label="FULL_DRAW",
            overall_score=99.9,
            professional_comparison="test",
            metrics={},
            joint_angles={},
            faults=[],
            strengths=[],
            recommendations=[],
            created_at=datetime.now(timezone.utc),
        )

    fake_module.analyze = fake_analyze
    monkeypatch.setitem(sys.modules, "ml.sports.archery.classifier", fake_module)

    result = run_pipeline(b"fake video bytes", SportType.ARCHERY)
    assert result.analysis_id == "real-model-ran"
    assert result.overall_score == 99.9
