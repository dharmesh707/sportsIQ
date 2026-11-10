from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.pipeline import Pipeline

from app.ml.dataset.builder import BuiltFeatureDataset


@dataclass(frozen=True)
class SplitEvaluation:
    split: str
    sample_count: int
    accuracy: float
    macro_f1: float
    weighted_f1: float
    labels: list[str]
    confusion_matrix: list[list[int]]
    classification_report: dict[str, Any]


@dataclass(frozen=True)
class BaselineTrainingResult:
    model: Pipeline
    feature_names: list[str]
    labels: list[str]
    train_sample_count: int
    validation: SplitEvaluation | None
    test: SplitEvaluation | None


def _validate_dataset(dataset: BuiltFeatureDataset) -> None:
    if not dataset.samples:
        raise ValueError("Cannot train on an empty dataset.")

    if not dataset.feature_names:
        raise ValueError("Dataset has no feature names.")

    if dataset.target_length < 1:
        raise ValueError("Dataset target_length must be positive.")

    expected_shape = (
        dataset.target_length,
        len(dataset.feature_names),
    )

    for sample in dataset.samples:
        values = np.asarray(sample.encoded_sequence.values, dtype=object)

        if values.shape != expected_shape:
            raise ValueError(
                f"Clip '{sample.clip_id}' has shape {values.shape}; "
                f"expected {expected_shape}."
            )

        if not sample.label:
            raise ValueError(f"Clip '{sample.clip_id}' has an empty label.")

        if sample.split not in {"train", "validation", "test"}:
            raise ValueError(
                f"Clip '{sample.clip_id}' has unsupported split "
                f"'{sample.split}'."
            )


def _flatten_samples(
    samples: list,
    *,
    target_length: int,
    feature_count: int,
) -> np.ndarray:
    expected_shape = (target_length, feature_count)
    flattened: list[np.ndarray] = []

    for sample in samples:
        sequence = np.asarray(sample.encoded_sequence.values, dtype=float)

        if sequence.shape != expected_shape:
            raise ValueError(
                f"Clip '{sample.clip_id}' has shape {sequence.shape}; "
                f"expected {expected_shape}."
            )

        flattened.append(sequence.reshape(-1))

    if not flattened:
        return np.empty((0, target_length * feature_count), dtype=float)

    return np.stack(flattened, axis=0)


def _evaluate(
    model: Pipeline,
    samples: list,
    *,
    split: str,
    target_length: int,
    feature_count: int,
    labels: list[str],
) -> SplitEvaluation | None:
    if not samples:
        return None

    x = _flatten_samples(
        samples,
        target_length=target_length,
        feature_count=feature_count,
    )
    y_true = [sample.label for sample in samples]
    y_pred = model.predict(x)

    matrix = confusion_matrix(
        y_true,
        y_pred,
        labels=labels,
    )

    report = classification_report(
        y_true,
        y_pred,
        labels=labels,
        output_dict=True,
        zero_division=0,
    )

    return SplitEvaluation(
        split=split,
        sample_count=len(samples),
        accuracy=float(accuracy_score(y_true, y_pred)),
        macro_f1=float(
            f1_score(
                y_true,
                y_pred,
                labels=labels,
                average="macro",
                zero_division=0,
            )
        ),
        weighted_f1=float(
            f1_score(
                y_true,
                y_pred,
                labels=labels,
                average="weighted",
                zero_division=0,
            )
        ),
        labels=labels,
        confusion_matrix=matrix.astype(int).tolist(),
        classification_report=report,
    )


def train_random_forest_baseline(
    dataset: BuiltFeatureDataset,
    *,
    random_state: int = 42,
    n_estimators: int = 300,
    min_samples_leaf: int = 2,
    class_weight: str | dict | None = "balanced",
) -> BaselineTrainingResult:
    """
    Train a Random Forest baseline using only manifest records assigned
    to the train split.

    Validation and test samples are used only for evaluation.
    """

    _validate_dataset(dataset)

    train_samples = [
        sample for sample in dataset.samples
        if sample.split == "train"
    ]
    validation_samples = [
        sample for sample in dataset.samples
        if sample.split == "validation"
    ]
    test_samples = [
        sample for sample in dataset.samples
        if sample.split == "test"
    ]

    if not train_samples:
        raise ValueError("No samples assigned to the train split.")

    train_labels = sorted({sample.label for sample in train_samples})

    if len(train_labels) < 2:
        raise ValueError(
            "Training requires at least two distinct classes in the train split."
        )

    feature_count = len(dataset.feature_names)

    x_train = _flatten_samples(
        train_samples,
        target_length=dataset.target_length,
        feature_count=feature_count,
    )
    y_train = [sample.label for sample in train_samples]

    model = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="median",
                    add_indicator=True,
                ),
            ),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=n_estimators,
                    min_samples_leaf=min_samples_leaf,
                    class_weight=class_weight,
                    random_state=random_state,
                    n_jobs=-1,
                ),
            ),
        ]
    )

    model.fit(x_train, y_train)

    # Report labels learned from the training split. Any unseen class in
    # validation/test is not silently added to the classifier's label set.
    validation_result = _evaluate(
        model,
        validation_samples,
        split="validation",
        target_length=dataset.target_length,
        feature_count=feature_count,
        labels=train_labels,
    )

    test_result = _evaluate(
        model,
        test_samples,
        split="test",
        target_length=dataset.target_length,
        feature_count=feature_count,
        labels=train_labels,
    )

    return BaselineTrainingResult(
        model=model,
        feature_names=list(dataset.feature_names),
        labels=train_labels,
        train_sample_count=len(train_samples),
        validation=validation_result,
        test=test_result,
    )