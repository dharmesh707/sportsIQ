
from __future__ import annotations

import pytest

from app.ml.dataset.builder import (
    BuiltFeatureDataset,
    DatasetFeatureSample,
)
from app.ml.features.sequence_encoder import EncodedTemporalSequence
from app.ml.training.baseline import train_random_forest_baseline


FEATURE_NAMES = [
    "left_elbow_angle",
    "right_elbow_angle",
]

TARGET_LENGTH = 3


def make_sample(
    *,
    clip_id: str,
    source_video_id: str,
    player_id: str,
    label: str,
    split: str,
    value: float,
) -> DatasetFeatureSample:
    """Create one synthetic encoded temporal sample."""

    encoded_sequence = EncodedTemporalSequence(
        values=[
            [value, value + 0.1],
            [value + 0.2, value + 0.3],
            [value + 0.4, value + 0.5],
        ],
        timestamps_ms=[0.0, 50.0, 100.0],
        feature_names=FEATURE_NAMES.copy(),
        target_length=TARGET_LENGTH,
        source_frame_count=3,
        feature_schema="sportsiq_temporal_features",
        feature_version="1.0.0",
    )

    return DatasetFeatureSample(
        clip_id=clip_id,
        label=label,
        source_video_id=source_video_id,
        player_id=player_id,
        session_id=f"session_{player_id}",
        split=split,
        start_ms=0.0,
        end_ms=100.0,
        encoded_sequence=encoded_sequence,
    )


def make_dataset() -> BuiltFeatureDataset:
    """Build a synthetic dataset with train, validation, and test splits."""

    samples: list[DatasetFeatureSample] = []

    # Training samples: two examples per class.
    training_examples = [
        ("train_smash_1", "smash", 1.0),
        ("train_smash_2", "smash", 1.2),
        ("train_clear_1", "clear", 5.0),
        ("train_clear_2", "clear", 5.2),
        ("train_drop_1", "drop", 9.0),
        ("train_drop_2", "drop", 9.2),
    ]

    for index, (clip_id, label, value) in enumerate(training_examples):
        samples.append(
            make_sample(
                clip_id=clip_id,
                source_video_id=f"video_{clip_id}",
                player_id=f"train_player_{index}",
                label=label,
                split="train",
                value=value,
            )
        )

    # Validation samples: one example per class.
    validation_examples = [
        ("validation_smash", "smash", 1.1),
        ("validation_clear", "clear", 5.1),
        ("validation_drop", "drop", 9.1),
    ]

    for index, (clip_id, label, value) in enumerate(validation_examples):
        samples.append(
            make_sample(
                clip_id=clip_id,
                source_video_id=f"video_{clip_id}",
                player_id=f"validation_player_{index}",
                label=label,
                split="validation",
                value=value,
            )
        )

    # Test samples: one example per class.
    test_examples = [
        ("test_smash", "smash", 1.15),
        ("test_clear", "clear", 5.15),
        ("test_drop", "drop", 9.15),
    ]

    for index, (clip_id, label, value) in enumerate(test_examples):
        samples.append(
            make_sample(
                clip_id=clip_id,
                source_video_id=f"video_{clip_id}",
                player_id=f"test_player_{index}",
                label=label,
                split="test",
                value=value,
            )
        )

    return BuiltFeatureDataset(
        samples=samples,
        feature_names=FEATURE_NAMES.copy(),
        target_length=TARGET_LENGTH,
        feature_schema="sportsiq_feature_dataset",
        feature_version="1.0.0",
    )


def test_baseline_trains_successfully():
    dataset = make_dataset()

    result = train_random_forest_baseline(
        dataset,
        random_state=42,
        n_estimators=50,
    )

    assert result.model is not None
    assert result.train_sample_count == 6
    assert result.feature_names == FEATURE_NAMES
    assert result.labels == ["clear", "drop", "smash"]


def test_baseline_returns_validation_evaluation():
    dataset = make_dataset()

    result = train_random_forest_baseline(
        dataset,
        random_state=42,
        n_estimators=50,
    )

    assert result.validation is not None
    assert result.validation.split == "validation"
    assert result.validation.sample_count == 3

    assert 0.0 <= result.validation.accuracy <= 1.0
    assert 0.0 <= result.validation.macro_f1 <= 1.0
    assert 0.0 <= result.validation.weighted_f1 <= 1.0


def test_baseline_returns_test_evaluation():
    dataset = make_dataset()

    result = train_random_forest_baseline(
        dataset,
        random_state=42,
        n_estimators=50,
    )

    assert result.test is not None
    assert result.test.split == "test"
    assert result.test.sample_count == 3

    assert 0.0 <= result.test.accuracy <= 1.0
    assert 0.0 <= result.test.macro_f1 <= 1.0
    assert 0.0 <= result.test.weighted_f1 <= 1.0


def test_baseline_evaluations_include_all_training_classes():
    dataset = make_dataset()

    result = train_random_forest_baseline(
        dataset,
        random_state=42,
        n_estimators=50,
    )

    expected_labels = ["clear", "drop", "smash"]

    assert result.labels == expected_labels
    assert result.validation is not None
    assert result.test is not None

    assert result.validation.labels == expected_labels
    assert result.test.labels == expected_labels


def test_baseline_confusion_matrix_has_expected_dimensions():
    dataset = make_dataset()

    result = train_random_forest_baseline(
        dataset,
        random_state=42,
        n_estimators=50,
    )

    assert result.validation is not None
    assert result.test is not None

    assert len(result.validation.confusion_matrix) == 3
    assert all(
        len(row) == 3
        for row in result.validation.confusion_matrix
    )

    assert len(result.test.confusion_matrix) == 3
    assert all(
        len(row) == 3
        for row in result.test.confusion_matrix
    )


def test_baseline_classification_report_contains_class_metrics():
    dataset = make_dataset()

    result = train_random_forest_baseline(
        dataset,
        random_state=42,
        n_estimators=50,
    )

    assert result.validation is not None

    report = result.validation.classification_report

    assert "clear" in report
    assert "drop" in report
    assert "smash" in report
    assert "macro avg" in report
    assert "weighted avg" in report


def test_baseline_is_deterministic():
    dataset = make_dataset()

    result_1 = train_random_forest_baseline(
        dataset,
        random_state=42,
        n_estimators=50,
    )

    result_2 = train_random_forest_baseline(
        dataset,
        random_state=42,
        n_estimators=50,
    )

    assert result_1.validation is not None
    assert result_2.validation is not None
    assert result_1.test is not None
    assert result_2.test is not None

    assert (
        result_1.validation.accuracy
        == result_2.validation.accuracy
    )

    assert result_1.test.accuracy == result_2.test.accuracy

    assert (
        result_1.validation.confusion_matrix
        == result_2.validation.confusion_matrix
    )

    assert (
        result_1.test.confusion_matrix
        == result_2.test.confusion_matrix
    )


def test_baseline_rejects_dataset_without_training_samples():
    validation_sample = make_sample(
        clip_id="validation_only",
        source_video_id="validation_video",
        player_id="validation_player",
        label="smash",
        split="validation",
        value=1.0,
    )

    dataset = BuiltFeatureDataset(
        samples=[validation_sample],
        feature_names=FEATURE_NAMES.copy(),
        target_length=TARGET_LENGTH,
        feature_schema="sportsiq_feature_dataset",
        feature_version="1.0.0",
    )

    with pytest.raises(
        ValueError,
        match="No samples assigned to the train split",
    ):
        train_random_forest_baseline(dataset)


def test_baseline_rejects_unknown_split_name():
    unknown_split_sample = make_sample(
        clip_id="unknown_split_clip",
        source_video_id="unknown_split_video",
        player_id="unknown_split_player",
        label="smash",
        split="testing",
        value=1.0,
    )

    dataset = BuiltFeatureDataset(
        samples=[unknown_split_sample],
        feature_names=FEATURE_NAMES.copy(),
        target_length=TARGET_LENGTH,
        feature_schema="sportsiq_feature_dataset",
        feature_version="1.0.0",
    )

    with pytest.raises(
        ValueError,
        match="unsupported split",
    ):
        train_random_forest_baseline(dataset)


def test_baseline_rejects_training_with_only_one_class():
    samples = [
        make_sample(
            clip_id=f"single_class_{index}",
            source_video_id=f"single_class_video_{index}",
            player_id=f"single_class_player_{index}",
            label="smash",
            split="train",
            value=1.0 + index,
        )
        for index in range(3)
    ]

    dataset = BuiltFeatureDataset(
        samples=samples,
        feature_names=FEATURE_NAMES.copy(),
        target_length=TARGET_LENGTH,
        feature_schema="sportsiq_feature_dataset",
        feature_version="1.0.0",
    )

    with pytest.raises(
        ValueError,
        match="at least two distinct classes",
    ):
        train_random_forest_baseline(dataset)


def test_baseline_rejects_incorrect_sequence_shape():
    sample = make_sample(
        clip_id="wrong_shape",
        source_video_id="wrong_shape_video",
        player_id="wrong_shape_player",
        label="smash",
        split="train",
        value=1.0,
    )

    incorrect_sequence = EncodedTemporalSequence(
        values=[
            [1.0, 1.1],
            [1.2, 1.3],
        ],
        timestamps_ms=[0.0, 50.0],
        feature_names=FEATURE_NAMES.copy(),
        target_length=2,
        source_frame_count=2,
        feature_schema="sportsiq_temporal_features",
        feature_version="1.0.0",
    )

    incorrect_sample = DatasetFeatureSample(
        clip_id=sample.clip_id,
        label=sample.label,
        source_video_id=sample.source_video_id,
        player_id=sample.player_id,
        session_id=sample.session_id,
        split=sample.split,
        start_ms=sample.start_ms,
        end_ms=sample.end_ms,
        encoded_sequence=incorrect_sequence,
    )

    dataset = BuiltFeatureDataset(
        samples=[incorrect_sample],
        feature_names=FEATURE_NAMES.copy(),
        target_length=TARGET_LENGTH,
        feature_schema="sportsiq_feature_dataset",
        feature_version="1.0.0",
    )

    with pytest.raises(
        ValueError,
        match="has shape",
    ):
        train_random_forest_baseline(dataset)
