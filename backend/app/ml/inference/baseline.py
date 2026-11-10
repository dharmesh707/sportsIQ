
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.ml.features.sequence_encoder import EncodedTemporalSequence
from app.ml.training.persistence import LoadedBaselineModel


@dataclass(frozen=True)
class BaselinePrediction:
    """Prediction output from a saved baseline model."""

    predicted_label: str
    probabilities: dict[str, float]
    model_version: str


def predict_baseline(
    loaded: LoadedBaselineModel,
    sequence: EncodedTemporalSequence,
) -> BaselinePrediction:
    """
    Predict a label from one encoded temporal sequence.

    Input must use the same feature ordering, temporal length,
    sequence schema, and sequence version used during training.
    """

    metadata = loaded.metadata

    if sequence.target_length != metadata.target_length:
        raise ValueError(
            f"Sequence target_length is {sequence.target_length}; "
            f"model expects {metadata.target_length}."
        )

    if sequence.feature_names != metadata.feature_names:
        raise ValueError(
            "Sequence feature names or ordering do not match the model."
        )

    if sequence.feature_schema != metadata.sequence_schema:
        raise ValueError(
            f"Sequence schema is {sequence.feature_schema!r}; "
            f"model expects {metadata.sequence_schema!r}."
        )

    if sequence.feature_version != metadata.sequence_version:
        raise ValueError(
            f"Sequence feature version is {sequence.feature_version!r}; "
            f"model expects {metadata.sequence_version!r}."
        )

    values = np.asarray(sequence.values, dtype=float)

    expected_shape = (
        metadata.target_length,
        len(metadata.feature_names),
    )

    if values.shape != expected_shape:
        raise ValueError(
            f"Sequence has shape {values.shape}; "
            f"model expects {expected_shape}."
        )

    flattened = values.reshape(1, -1)

    predicted = loaded.model.predict(flattened)
    probabilities = loaded.model.predict_proba(flattened)[0]

    probability_map = {
        str(label): float(probability)
        for label, probability in zip(
            loaded.model.classes_,
            probabilities,
        )
    }

    return BaselinePrediction(
        predicted_label=str(predicted[0]),
        probabilities=probability_map,
        model_version=metadata.model_version,
    )
