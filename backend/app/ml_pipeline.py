"""
Single entry point for the ML pipeline: run_pipeline(video_bytes, sport_type) -> AnalysisResult.

Lives in backend/app/ (not top-level ml/) so Python can import it without
path issues when running uvicorn from backend/. The actual per-sport model
code still lives in the repo-root ml/ folder per brief section 5 - this file
just adds repo root to sys.path once so "import ml.sports.<sport>.classifier"
works.

PLUG-AND-PLAY CONTRACT for whoever wires in the real model (teammate 2):
Create ml/sports/<sport_type>/classifier.py at repo root with exactly one
function:

    def analyze(video_bytes: bytes) -> AnalysisResult

- Import AnalysisResult from app.schemas.analysis, return that exact type,
  every field populated per API_CONTRACT.md.
- Call whatever helpers you build in ml/pose/ and ml/angles/ internally
  (scaffold folders only right now - no real code yet, build what you need).
- The moment ml/sports/<sport>/classifier.py exists and defines analyze(),
  this file auto-detects it and routes real video there instead of mock data.
  No router change, no contract change, nothing else to touch.
- Until then, every sport silently falls back to the Day 1 mock generator -
  the API never breaks because a classifier isn't ready yet.
"""

import importlib
import logging
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]  # backend/app/ml_pipeline.py -> repo root
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.schemas.analysis import AnalysisResult
from app.schemas.common import SportType
from app.services.mock_data import build_mock_analysis

logger = logging.getLogger(__name__)

_SPORT_MODULE_PATHS: dict[SportType, str] = {
    SportType.BADMINTON: "ml.sports.badminton.classifier",
    SportType.TENNIS: "ml.sports.tennis.classifier",
    SportType.TABLE_TENNIS: "ml.sports.table_tennis.classifier",
    SportType.CRICKET_BOWLING: "ml.sports.cricket_bowling.classifier",
    SportType.ARCHERY: "ml.sports.archery.classifier",
}


def run_pipeline(video_bytes: bytes, sport_type: SportType) -> AnalysisResult:
    module_path = _SPORT_MODULE_PATHS[sport_type]
    try:
        module = importlib.import_module(module_path)
        analyze_fn = getattr(module, "analyze")
    except (ImportError, AttributeError):
        logger.info(
            "No real classifier at %s yet for %s - using mock data.",
            module_path, sport_type.value,
        )
        return build_mock_analysis(sport_type)

    result = analyze_fn(video_bytes)
    if not isinstance(result, AnalysisResult):
        logger.warning(
            "%s.analyze() did not return AnalysisResult - falling back to mock.",
            module_path,
        )
        return build_mock_analysis(sport_type)
    return result

