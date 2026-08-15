"""
Shared Pydantic base config.

CONTRACT RULE #1: every response model in every router MUST use this config.
Import CamelModel and subclass it — never re-declare model_config by hand.
See API_CONTRACT.md at the repo root for the source of truth this file implements.
"""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """
    Base model that serializes snake_case Python fields as camelCase JSON.

    populate_by_name=True means you can still construct instances using the
    snake_case field name in Python code (e.g. AnalysisResult(analysis_id=...)),
    while .model_dump(by_alias=True) / the FastAPI response emits camelCase.

    FastAPI note: routers must return responses with by_alias behavior enabled.
    We set this globally in main.py's default response class, so individual
    routers do NOT need to call model_dump(by_alias=True) manually — but if you
    ever return a raw dict instead of a model instance, camelCase will NOT be
    applied automatically. Always return model instances, not dicts.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
