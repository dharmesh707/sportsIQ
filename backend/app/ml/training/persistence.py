
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import joblib
import sklearn

from app.ml.dataset.builder import BuiltFeatureDataset
from app.ml.training.baseline import BaselineTrainingResult


@dataclass(frozen=True)
class BaselineModelMetadata:
    """Metadata required to validate and use a saved baseline model."""

    model_type: str
    model_version: str
    feature_names: list[str]
    target_length: int
    feature_schema: str
    feature_version: str
    sequence_schema: str
    sequence_version: str
    labels: list[str]
    train_sample_count: int
    sklearn_version: str
    training_config: dict[str, Any]


@dataclass(frozen=True)
class LoadedBaselineModel:
    """A fitted model paired with its validated metadata."""

    model: Any
    metadata: BaselineModelMetadata


def _metadata_path(model_path: Path) -> Path:
    """Return the metadata path associated with a model artifact."""

    return model_path.with_suffix(".json")


def save_baseline_model(
    result: BaselineTrainingResult,
    dataset: BuiltFeatureDataset,
    model_path: str | Path,
    *,
    model_version: str = "1.0.0",
) -> tuple[Path, Path]:
    """
    Save a fitted baseline model and its metadata.

    Produces:
        model_path: serialized scikit-learn Pipeline
        metadata_path: JSON metadata next to the model
    """

    model_path = Path(model_path)
    metadata_path = _metadata_path(model_path)

    if not result.feature_names:
        raise ValueError("Training result has no feature names.")

    if result.feature_names != dataset.feature_names:
        raise ValueError(
            "Training result feature names do not match the dataset."
        )

    if result.labels != sorted(result.labels):
        raise ValueError(
            "Training result labels must be in deterministic sorted order."
        )

    if not dataset.samples:
        raise ValueError("Cannot save a model from an empty dataset.")

    first_sequence = dataset.samples[0].encoded_sequence

    for sample in dataset.samples:
        sequence = sample.encoded_sequence

        if sequence.feature_names != dataset.feature_names:
            raise ValueError(
                f"Feature names mismatch for clip '{sample.clip_id}'."
            )

        if sequence.target_length != dataset.target_length:
            raise ValueError(
                f"Target length mismatch for clip '{sample.clip_id}'."
            )

        if sequence.feature_schema != first_sequence.feature_schema:
            raise ValueError(
                "Encoded sequence schema mismatch across dataset samples."
            )

        if sequence.feature_version != first_sequence.feature_version:
            raise ValueError(
                "Encoded sequence version mismatch across dataset samples."
            )

    classifier = result.model.named_steps.get("classifier")

    if classifier is None:
        raise ValueError(
            "The fitted pipeline does not contain a classifier step."
        )

    metadata = BaselineModelMetadata(
        model_type="random_forest_baseline",
        model_version=model_version,
        feature_names=list(dataset.feature_names),
        target_length=dataset.target_length,
        feature_schema=dataset.feature_schema,
        feature_version=dataset.feature_version,
        sequence_schema=first_sequence.feature_schema,
        sequence_version=first_sequence.feature_version,
        labels=list(result.labels),
        train_sample_count=result.train_sample_count,
        sklearn_version=sklearn.__version__,
        training_config={
            "classifier": type(classifier).__name__,
            "n_estimators": classifier.n_estimators,
            "min_samples_leaf": classifier.min_samples_leaf,
            "class_weight": classifier.class_weight,
            "random_state": classifier.random_state,
        },
    )

    model_path.parent.mkdir(parents=True, exist_ok=True)

    joblib.dump(result.model, model_path)

    metadata_path.write_text(
        json.dumps(asdict(metadata), indent=2),
        encoding="utf-8",
    )

    return model_path, metadata_path


def load_baseline_model(
    model_path: str | Path,
    *,
    metadata_path: str | Path | None = None,
) -> LoadedBaselineModel:
    """
    Load a saved baseline pipeline and its JSON metadata.

    Only load artifacts from trusted sources. joblib uses Python
    serialization and must not be treated as safe for untrusted files.
    """

    model_path = Path(model_path)

    if metadata_path is None:
        metadata_path = _metadata_path(model_path)
    else:
        metadata_path = Path(metadata_path)

    if not model_path.is_file():
        raise FileNotFoundError(
            f"Model artifact not found: {model_path}"
        )

    if not metadata_path.is_file():
        raise FileNotFoundError(
            f"Model metadata not found: {metadata_path}"
        )

    raw_metadata = json.loads(
        metadata_path.read_text(encoding="utf-8")
    )

    metadata = BaselineModelMetadata(**raw_metadata)

    if metadata.model_type != "random_forest_baseline":
        raise ValueError(
            f"Unsupported model type: {metadata.model_type!r}"
        )

    if metadata.target_length < 1:
        raise ValueError("Model metadata target_length must be positive.")

    if not metadata.feature_names:
        raise ValueError("Model metadata has no feature names.")

    if not metadata.labels:
        raise ValueError("Model metadata has no labels.")

    model = joblib.load(model_path)

    if not hasattr(model, "predict"):
        raise ValueError("Loaded artifact does not support prediction.")

    if not hasattr(model, "predict_proba"):
        raise ValueError(
            "Loaded artifact does not support probability prediction."
        )

    model_classes = list(model.classes_)

    if model_classes != metadata.labels:
        raise ValueError(
            "Model classes do not match the metadata labels."
        )

    return LoadedBaselineModel(
        model=model,
        metadata=metadata,
    )
