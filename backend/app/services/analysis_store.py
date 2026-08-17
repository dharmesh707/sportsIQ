"""
Real persistence for AnalysisResult, replacing mock_store.py's in-memory
dict. Converts between the Pydantic AnalysisResult (what routers/pipeline
work with) and AnalysisRecord/FaultRecord (what's actually stored), so
callers never touch SQLAlchemy models directly.
"""
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.analysis import AnalysisRecord, FaultRecord
from app.schemas.analysis import AnalysisResult, Fault


def save(db: Session, user_id: str, result: AnalysisResult) -> None:
    record = AnalysisRecord(
        id=result.analysis_id,
        user_id=user_id,
        sport_type=result.sport_type.value,
        action_label=result.action_label,
        overall_score=result.overall_score,
        professional_comparison=result.professional_comparison,
        metrics=result.metrics,
        joint_angles=result.joint_angles,
        strengths=result.strengths,
        recommendations=result.recommendations,
        created_at=result.created_at,
    )
    record.faults = [
        FaultRecord(
            fault_code=f.fault_code,
            type=f.type.value,
            description=f.description,
            frame=f.frame,
            reference_source=f.reference_source,
        )
        for f in result.faults
    ]
    db.add(record)
    db.commit()


def _to_analysis_result(record: AnalysisRecord) -> AnalysisResult:
    return AnalysisResult(
        analysis_id=record.id,
        sport_type=record.sport_type,
        action_label=record.action_label,
        overall_score=record.overall_score,
        professional_comparison=record.professional_comparison,
        metrics=record.metrics,
        joint_angles=record.joint_angles,
        faults=[
            Fault(
                fault_code=f.fault_code,
                type=f.type,
                description=f.description,
                frame=f.frame,
                reference_source=f.reference_source,
            )
            for f in record.faults
        ],
        strengths=record.strengths,
        recommendations=record.recommendations,
        created_at=record.created_at,
    )


def list_for_user(db: Session, user_id: str) -> list[AnalysisResult]:
    records = (
        db.query(AnalysisRecord)
        .filter(AnalysisRecord.user_id == user_id)
        .order_by(desc(AnalysisRecord.created_at))
        .all()
    )
    return [_to_analysis_result(r) for r in records]


def get_by_id(db: Session, user_id: str, analysis_id: str) -> AnalysisResult | None:
    record = (
        db.query(AnalysisRecord)
        .filter(AnalysisRecord.id == analysis_id, AnalysisRecord.user_id == user_id)
        .first()
    )
    return _to_analysis_result(record) if record else None
