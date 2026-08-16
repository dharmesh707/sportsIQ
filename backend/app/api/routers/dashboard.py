from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser
from app.schemas.analysis import AnalysisResult
from app.schemas.common import SportType
from app.schemas.dashboard import (
    DashboardResponse,
    DashboardSummary,
    FaultOccurrence,
    FaultTrend,
    ProgressBaseline,
    ProgressDataPoint,
    ProgressRange,
    ProgressResponse,
    RecentSession,
    SportBreakdown,
    TopFault,
)
from app.services import mock_store

router = APIRouter(tags=["analysis"])

_RANGE_DAYS = {"7d": 7, "30d": 30, "90d": 90, "all": None}


def _hard_soft_counts(analysis: AnalysisResult) -> tuple[int, int]:
    hard = sum(1 for f in analysis.faults if f.type.value == "hard")
    soft = sum(1 for f in analysis.faults if f.type.value == "soft")
    return hard, soft


def _current_streak_days(analyses: list[AnalysisResult]) -> int:
    """
    Consecutive calendar days (in UTC) with at least one session, counting
    back from today or yesterday. analyses is newest-first. A gap of more
    than 1 day breaks the streak. Today having zero sessions yet doesn't
    break a streak that's still live from yesterday.
    """
    if not analyses:
        return 0
    session_dates = sorted({a.created_at.date() for a in analyses}, reverse=True)
    today = datetime.now(timezone.utc).date()
    most_recent = session_dates[0]
    gap_from_today = (today - most_recent).days
    if gap_from_today > 1:
        return 0  # streak already broken - last session was 2+ days ago
    streak = 1
    for i in range(1, len(session_dates)):
        expected_prev = session_dates[i - 1] - timedelta(days=1)
        if session_dates[i] == expected_prev:
            streak += 1
        else:
            break
    return streak

def _trend_for(sport_analyses: list[AnalysisResult]) -> str:
    # sport_analyses is newest-first (mock_store inserts newest-first)
    if len(sport_analyses) < 3:
        return "insufficient_data"
    latest = sport_analyses[0].overall_score
    prior = sport_analyses[1:]
    prior_avg = sum(a.overall_score for a in prior) / len(prior)
    diff = latest - prior_avg
    if diff > 5:
        return "improving"
    if diff < -5:
        return "declining"
    return "stable"


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(current_user: CurrentUser) -> DashboardResponse:
    analyses = mock_store.list_for_user(current_user.id)  # newest-first

    if not analyses:
        return DashboardResponse(
            summary=DashboardSummary(
                total_sessions=0,
                sports_practiced=[],
                current_streak_days=0,
                last_session_at=None,
            ),
            sport_breakdown=[],
            recent_sessions=[],
            top_faults=[],
            recommendations=[],
        )

    by_sport: dict[SportType, list[AnalysisResult]] = defaultdict(list)
    for a in analyses:
        by_sport[a.sport_type].append(a)  # preserves newest-first within each sport

    sport_breakdown = [
        SportBreakdown(
            sport_type=sport,
            session_count=len(items),
            average_score=round(sum(a.overall_score for a in items) / len(items), 1),
            last_session_at=items[0].created_at,
            trend=_trend_for(items),
        )
        for sport, items in by_sport.items()
    ]

    recent_sessions = []
    for a in analyses[:5]:
        hard, soft = _hard_soft_counts(a)
        recent_sessions.append(
            RecentSession(
                session_id=a.analysis_id,
                sport_type=a.sport_type,
                score=a.overall_score,
                hard_fault_count=hard,
                soft_fault_count=soft,
                created_at=a.created_at,
            )
        )

    fault_counts: dict[tuple[str, SportType, str], int] = defaultdict(int)
    for a in analyses:
        for f in a.faults:
            fault_counts[(f.fault_code, a.sport_type, f.type.value)] += 1
    top_faults = [
        TopFault(fault_code=code, sport_type=sport, fault_type=ftype, occurrence_count=count)
        for (code, sport, ftype), count in sorted(
            fault_counts.items(), key=lambda kv: kv[1], reverse=True
        )[:5]
    ]

    # Simple recommendation pull: dedupe across recent sessions, cap at 5.
    seen: set[str] = set()
    recommendations: list[str] = []
    for a in analyses[:5]:
        for rec in a.recommendations:
            if rec not in seen:
                seen.add(rec)
                recommendations.append(rec)

    return DashboardResponse(
        summary=DashboardSummary(
            total_sessions=len(analyses),
            sports_practiced=list(by_sport.keys()),
            current_streak_days=_current_streak_days(analyses),
            last_session_at=analyses[0].created_at,
        ),
        sport_breakdown=sport_breakdown,
        recent_sessions=recent_sessions,
        top_faults=top_faults,
        recommendations=recommendations[:5],
    )


@router.get("/progress", response_model=ProgressResponse)
def get_progress(
    current_user: CurrentUser,
    sportType: SportType = Query(...),  # noqa: N803 - contract field naming
    range: str = Query("30d"),
) -> ProgressResponse:
    days = _RANGE_DAYS.get(range, 30)
    all_analyses = [
        a for a in mock_store.list_for_user(current_user.id) if a.sport_type == sportType
    ]
    if days is not None:
        cutoff = datetime.now(timezone.utc).timestamp() - days * 86400
        all_analyses = [a for a in all_analyses if a.created_at.timestamp() >= cutoff]

    today = date.today()
    if not all_analyses:
        return ProgressResponse(
            sport_type=sportType,
            range=ProgressRange(start=today, end=today),
            baseline=ProgressBaseline(
                initial_score=0, current_score=0, percent_change=0, established_at=today
            ),
            data_points=[],
            fault_trends=[],
        )

    # oldest-first for the time series and baseline math
    chronological = sorted(all_analyses, key=lambda a: a.created_at)

    data_points = []
    fault_by_code: dict[str, dict[str, object]] = {}
    for a in chronological:
        hard, soft = _hard_soft_counts(a)
        data_points.append(
            ProgressDataPoint(
                date=a.created_at.date(),
                session_id=a.analysis_id,
                score=a.overall_score,
                hard_fault_count=hard,
                soft_fault_count=soft,
            )
        )
        for f in a.faults:
            entry = fault_by_code.setdefault(
                f.fault_code, {"type": f.type.value, "occurrences": defaultdict(int)}
            )
            entry["occurrences"][a.created_at.date()] += 1

    fault_trends = [
        FaultTrend(
            fault_code=code,
            fault_type=info["type"],
            occurrences=[
                FaultOccurrence(date=d, count=c)
                for d, c in sorted(info["occurrences"].items())
            ],
        )
        for code, info in fault_by_code.items()
    ]

    initial = chronological[0].overall_score
    current = chronological[-1].overall_score
    percent_change = round(((current - initial) / initial) * 100, 1) if initial else 0.0

    return ProgressResponse(
        sport_type=sportType,
        range=ProgressRange(start=chronological[0].created_at.date(), end=today),
        baseline=ProgressBaseline(
            initial_score=initial,
            current_score=current,
            percent_change=percent_change,
            established_at=chronological[0].created_at.date(),
        ),
        data_points=data_points,
        fault_trends=fault_trends,
    )

