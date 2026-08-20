"""
Transparent feature-distance baseline for athlete comparison.

This is deliberately NOT a machine-learning model. The repository contains
two hand-authored reference profiles and zero labelled skill-level examples,
which is not a training set. Fitting anything supervised on it would produce
a model whose apparent accuracy is an artefact of the numbers someone typed
into a JSON file. See docs/TECHNIQUE_METHODOLOGY.md for the full argument.

What this does instead, per feature:

    similarity_i = clamp(1 - |user_i - reference_i| / tolerance_i, 0, 1)

then a weighted mean across features gives the overall similarity. Every
input is a real measured angle from the contact frame; every threshold comes
from config.py. Nothing here is estimated from data that does not exist.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from app.services.technique.config import (
    FEATURE_SPECS,
    FEATURE_SPEC_BY_KEY,
    LEVEL_BANDS,
    LEVEL_DESCRIPTIONS,
    STRENGTH_SIMILARITY_MIN,
    VERDICT_GOOD,
    VERDICT_NEEDS_WORK,
    VERDICT_SLIGHT,
    WEAKNESS_SIMILARITY_MAX,
    band_for,
)
from app.services.technique.reference_profiles import (
    ReferenceProfile,
    load_profiles,
)


@dataclass(frozen=True)
class FeatureComparison:
    key: str
    label: str
    unit: str
    user_value: float
    reference_value: float
    deviation: float  # signed: user - reference
    abs_deviation: float
    similarity: float  # 0-100
    verdict: str  # GOOD | SLIGHT_DIFFERENCE | NEEDS_IMPROVEMENT
    weight: float


@dataclass(frozen=True)
class ProfileMatch:
    profile_id: str
    display_name: str
    similarity: float  # 0-100
    provenance: str
    is_validated: bool


@dataclass
class ComparisonResult:
    closest: ProfileMatch
    all_matches: list[ProfileMatch]
    features: list[FeatureComparison]
    overall_similarity: float
    level: str
    level_description: str
    comparison_basis: str
    strengths: list[FeatureComparison] = field(default_factory=list)
    weaknesses: list[FeatureComparison] = field(default_factory=list)


def _finite(value: float | None) -> float | None:
    """
    Reject NaN/inf/None up front.

    MediaPipe can hand back degenerate landmarks (all-zero vectors give a
    zero-denominator angle), and one NaN silently poisons the whole weighted
    mean. Features that fail this check are excluded from the comparison
    entirely rather than being defaulted to a made-up number.
    """
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def _verdict(abs_deviation: float, key: str) -> str:
    spec = FEATURE_SPEC_BY_KEY[key]
    if abs_deviation <= spec.good_deg:
        return VERDICT_GOOD
    if abs_deviation <= spec.slight_deg:
        return VERDICT_SLIGHT
    return VERDICT_NEEDS_WORK


def compare_to_profile(
    user_features: dict[str, float], profile: ReferenceProfile
) -> tuple[list[FeatureComparison], float]:
    """Compare one feature vector against one profile. Returns (features, overall 0-100)."""
    comparisons: list[FeatureComparison] = []
    weighted_sum = 0.0
    total_weight = 0.0

    for spec in FEATURE_SPECS:
        user_value = _finite(user_features.get(spec.key))
        reference_value = _finite(profile.features.get(spec.key))
        if user_value is None or reference_value is None:
            # Missing on either side -> excluded, not guessed.
            continue

        deviation = user_value - reference_value
        abs_deviation = abs(deviation)
        tolerance = spec.tolerance_deg if spec.tolerance_deg > 0 else 1.0
        similarity = max(0.0, min(1.0, 1.0 - abs_deviation / tolerance)) * 100.0

        comparisons.append(
            FeatureComparison(
                key=spec.key,
                label=spec.label,
                unit=spec.unit,
                user_value=round(user_value, 1),
                reference_value=round(reference_value, 1),
                deviation=round(deviation, 1),
                abs_deviation=round(abs_deviation, 1),
                similarity=round(similarity, 1),
                verdict=_verdict(abs_deviation, spec.key),
                weight=spec.weight,
            )
        )
        weighted_sum += similarity * spec.weight
        total_weight += spec.weight

    overall = round(weighted_sum / total_weight, 1) if total_weight > 0 else 0.0
    return comparisons, overall


def _basis_sentence(profile: ReferenceProfile, validated: bool) -> str:
    if validated:
        return (
            f"Technique similarity to measured reference data for "
            f"{profile.display_name}."
        )
    return (
        f"Technique similarity to the '{profile.display_name}' reference profile - "
        "a hand-authored set of target joint angles, not measured athlete "
        "performance data."
    )


def compare(user_features: dict[str, float]) -> ComparisonResult | None:
    """
    Compare the user's contact-frame features against every reference profile.

    Returns None when no feature could be compared at all (every value was
    missing or non-finite), so the caller can degrade honestly instead of
    reporting a 0% similarity that would read as "very bad technique" when it
    actually means "we measured nothing".
    """
    profiles = load_profiles()
    scored: list[tuple[ReferenceProfile, list[FeatureComparison], float]] = []

    for profile in profiles:
        comparisons, overall = compare_to_profile(user_features, profile)
        if comparisons:
            scored.append((profile, comparisons, overall))

    if not scored:
        return None

    scored.sort(key=lambda item: item[2], reverse=True)
    best_profile, best_features, best_overall = scored[0]

    matches = [
        ProfileMatch(
            profile_id=p.id,
            display_name=p.display_name,
            similarity=overall,
            provenance=p.provenance,
            is_validated=p.is_validated,
        )
        for p, _, overall in scored
    ]

    level = band_for(best_overall, LEVEL_BANDS, default="BEGINNER")

    strengths = sorted(
        [f for f in best_features if f.similarity >= STRENGTH_SIMILARITY_MIN],
        key=lambda f: f.similarity,
        reverse=True,
    )
    weaknesses = sorted(
        [f for f in best_features if f.similarity <= WEAKNESS_SIMILARITY_MAX],
        key=lambda f: f.similarity,
    )

    return ComparisonResult(
        closest=matches[0],
        all_matches=matches,
        features=best_features,
        overall_similarity=best_overall,
        level=level,
        level_description=LEVEL_DESCRIPTIONS.get(level, ""),
        comparison_basis=_basis_sentence(best_profile, best_profile.is_validated),
        strengths=strengths,
        weaknesses=weaknesses,
    )
