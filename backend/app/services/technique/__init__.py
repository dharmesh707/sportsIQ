"""
Technique analysis layer: pose quality, reference-profile comparison,
estimated level, and deterministic recommendations.

Sport-agnostic by construction - it consumes a plain
`dict[str, float]` of contact-frame joint angles, so a second sport only
needs its own FEATURE_SPECS and reference profile file, not a fork of this
package.
"""

from app.services.technique import comparison, config, quality, recommendations
from app.services.technique.reference_profiles import load_profiles

__all__ = ["comparison", "config", "quality", "recommendations", "load_profiles"]
