
from __future__ import annotations

import json

import pytest

from app.ml.dataset.builder import BuiltFeatureDataset
from app.ml.features.sequence_encoder import EncodedTemporalSequence
from app.ml.inference.baseline import predict_baseline
from app.ml.training.baseline import train_random_forest_baseline
from app.ml.training.persistence import (
    load_baseline_model,
    save_baseline_model,
)

from app.tests.test_baseline_training import make_dataset


def test_save_and_load_baseline_model(tmp_path):
    dataset = make_dataset()

    result = train_random_forest_baseline(
        dataset,
        random_state=42,
        n_estimators=50,
    )

    model_path = tmp_path / "sportsiq_baseline.joblib"

    saved_model_path, saved_metadata_path = save_baseline_model(
        result,
        dataset,
        model_path,
    )

    assert saved_model_path.is_file()
    assert saved_metadata_path.is_file()

    loaded = load_baseline_model(saved_model_path)

    assert loaded.metadata.model_type == "random_forest_baseline"
    assert loaded.metadata.feature_names == dataset.feature_names
    assert loaded.metadata.target_length == dataset.target_length
    assert loaded.metadata.labels == result.labels
    assert loaded.metadata.train_sample_count == result.train_sample_count


def test_prediction_matches_before_and_after_model_reload(tmp_path):
    dataset = make_dataset()

    result = train_random_forest_baseline(
        dataset,
        random_state=42,
        n_estimators=50,
    )

    model_path = tmp_path / "sportsiq_baseline.joblib"

    save_baseline_model(
        result,
        dataset,
        model_path,
    )

    loaded = load_baseline_model(model_path)

    sequence = dataset.samples[0].encoded_sequence

    prediction = predict_baseline(
        loaded,
        sequence,
    )

    direct_prediction = result.model.predict(
        [
            [
                value
                for frame in sequence.values
                for value in frame
            ]
        ]
    )[0]

    assert prediction.predicted_label == direct_prediction
    assert prediction.model_version == "1.0.0"

    assert set(prediction.probabilities) == set(result.labels)

    assert sum(prediction.probabilities.values()) == pytest.approx(1.0)


def test_prediction_rejects_wrong_sequence_length(tmp_path):
    dataset = make_dataset()

    result = train_random_forest_baseline(
        dataset,
        random_state=42,
        n_estimators=50,
    )

    model_path = tmp_path / "sportsiq_baseline.joblib"

    save_baseline_model(
        result,
        dataset,
        model_path,
    )

    loaded = load_baseline_model(model_path)

    wrong_length_sequence = EncodedTemporalSequence(
        values=[
            [1.0, 1.1],
            [1.2, 1.3],
        ],
        timestamps_ms=[0.0, 50.0],
        feature_names=dataset.feature_names.copy(),
        target_length=2,
        source_frame_count=2,
        feature_schema="sportsiq_temporal_features",
        feature_version="1.0.0",
    )

    with pytest.raises(
        ValueError,
        match="target_length",
    ):
        predict_baseline(
            loaded,
            wrong_length_sequence,
        )


def test_prediction_rejects_wrong_feature_order(tmp_path):
    dataset = make_dataset()

    result = train_random_forest_baseline(
        dataset,
        random_state=42,
        n_estimators=50,
    )

    model_path = tmp_path / "sportsiq_baseline.joblib"

    save_baseline_model(
        result,
        dataset,
        model_path,
    )

    loaded = load_baseline_model(model_path)

    original = dataset.samples[0].encoded_sequence

    wrong_order_sequence = EncodedTemporalSequence(
        values=[
            [frame[1], frame[0]]
            for frame in original.values
        ],
        timestamps_ms=original.timestamps_ms,
        feature_names=[
            "right_elbow_angle",
            "left_elbow_angle",
        ],
        target_length=original.target_length,
        source_frame_count=original.source_frame_count,
        feature_schema=original.feature_schema,
        feature_version=original.feature_version,
    )

    with pytest.raises(
        ValueError,
        match="feature names or ordering",
    ):
        predict_baseline(
            loaded,
            wrong_order_sequence,
        )


def test_loader_rejects_missing_model(tmp_path):
    model_path = tmp_path / "missing_model.joblib"

    with pytest.raises(FileNotFoundError):
        load_baseline_model(model_path)


def test_loader_rejects_metadata_class_mismatch(tmp_path):
    dataset = make_dataset()

    result = train_random_forest_baseline(
        dataset,
        random_state=42,
        n_estimators=50,
    )

    model_path = tmp_path / "sportsiq_baseline.joblib"

    _, metadata_path = save_baseline_model(
        result,
        dataset,
        model_path,
    )

    metadata = json.loads(
        metadata_path.read_text(encoding="utf-8")
    )

    metadata["labels"] = ["clear", "drop"]

    metadata_path.write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Model classes do not match",
    ):
        load_baseline_model(model_path)
