"""Tests for _current_streak_days() - dashboard router streak calculation."""
from datetime import datetime, timedelta, timezone

from app.api.routers.dashboard import _current_streak_days
from app.schemas.analysis import AnalysisResult
from app.schemas.common import SportType


def _fake_analysis(days_ago: int) -> AnalysisResult:
    created = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return AnalysisResult(
        analysis_id=f"a-{days_ago}",
        sport_type=SportType.BADMINTON,
        action_label="FH_SMASH",
        overall_score=80.0,
        professional_comparison="test",
        metrics={},
        joint_angles={},
        faults=[],
        strengths=[],
        recommendations=[],
        created_at=created,
    )


def test_no_sessions_is_zero_streak():
    assert _current_streak_days([]) == 0


def test_single_session_today_is_streak_of_one():
    assert _current_streak_days([_fake_analysis(0)]) == 1


def test_three_consecutive_days_is_streak_of_three():
    analyses = [_fake_analysis(0), _fake_analysis(1), _fake_analysis(2)]
    assert _current_streak_days(analyses) == 3


def test_gap_breaks_streak_at_the_gap():
    # sessions today, yesterday, then a 2-day gap, then older sessions
    analyses = [_fake_analysis(0), _fake_analysis(1), _fake_analysis(4), _fake_analysis(5)]
    assert _current_streak_days(analyses) == 2


def test_last_session_two_days_ago_means_streak_already_broken():
    analyses = [_fake_analysis(2), _fake_analysis(3)]
    assert _current_streak_days(analyses) == 0


def test_last_session_yesterday_still_counts_as_live_streak():
    # today has no session yet, but yesterday does - streak isn't dead
    analyses = [_fake_analysis(1), _fake_analysis(2)]
    assert _current_streak_days(analyses) == 2


def test_multiple_sessions_same_day_count_once():
    analyses = [_fake_analysis(0), _fake_analysis(0), _fake_analysis(1)]
    assert _current_streak_days(analyses) == 2
