from dataclasses import replace

import numpy as np
import pytest
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from bhns.constants import FLUX_COLUMNS
from bhns.data.preprocessing import TrainingOnlyPreprocessor
from bhns.evaluation.grouped_cv import grouped_folds
from bhns.evaluation.splits import SourceLeakageError, add_inner_validation, dataset_fingerprint


def _separated_frame_and_fold(observations):
    fold = add_inner_validation(observations, grouped_folds(observations, n_splits=3)[0], validation_fraction=0.3)
    observations.loc[list(fold.test), list(FLUX_COLUMNS)] += 10000.0
    observations.loc[list(fold.validation), list(FLUX_COLUMNS)] += 2000.0
    # A new split must be bound to the updated test fixture, just as raw data are frozen before splitting.
    return observations, replace(fold, dataset_fingerprint=dataset_fingerprint(observations))


def test_scaler_sees_training_only_not_validation_or_test(observations):
    frame, fold = _separated_frame_and_fold(observations)
    preprocessor = TrainingOnlyPreprocessor().fit(frame, fold)
    expected = frame.iloc[list(fold.train)][list(FLUX_COLUMNS)].mean().to_numpy()
    np.testing.assert_allclose(preprocessor.pipeline_.named_steps["scaler"].mean_, expected)
    assert not np.allclose(expected, frame[list(FLUX_COLUMNS)].mean())
    before = preprocessor.pipeline_.named_steps["scaler"].mean_.copy()
    for partition in ["train", "validation", "test"]:
        preprocessor.transform(frame, partition=partition)
    np.testing.assert_array_equal(before, preprocessor.pipeline_.named_steps["scaler"].mean_)
    assert set(preprocessor.fit_obs_ids_) == set(frame.iloc[list(fold.train)].obs_id)
    assert set(preprocessor.fit_obs_ids_).isdisjoint(frame.iloc[list(fold.test)].obs_id)


def test_imputer_uses_training_median(observations):
    frame, fold = _separated_frame_and_fold(observations)
    frame.loc[fold.train[0], "flux_00"] = np.nan
    frame.loc[fold.test[0], "flux_00"] = np.nan
    fold = replace(fold, dataset_fingerprint=dataset_fingerprint(frame))
    p = TrainingOnlyPreprocessor(imputation="median").fit(frame, fold)
    expected = frame.iloc[list(fold.train)].flux_00.median()
    assert p.pipeline_.named_steps["imputer"].statistics_[0] == expected
    assert np.isfinite(p.transform(frame, partition="test")).all()


def test_pca_components_match_training_only_fit(observations):
    frame, fold = _separated_frame_and_fold(observations)
    p = TrainingOnlyPreprocessor(pca_components=3).fit(frame, fold)
    x = frame.iloc[list(fold.train)][list(FLUX_COLUMNS)].to_numpy()
    expected = PCA(n_components=3, random_state=42).fit(StandardScaler().fit_transform(x))
    np.testing.assert_allclose(p.pipeline_.named_steps["pca"].components_, expected.components_)


def test_all_missing_train_column_does_not_use_test_values(observations):
    fold = grouped_folds(observations, n_splits=3)[0]
    observations.loc[list(fold.train), "flux_00"] = np.nan
    fold = replace(fold, dataset_fingerprint=dataset_fingerprint(observations))
    with pytest.raises(ValueError, match="all-missing"):
        TrainingOnlyPreprocessor(imputation="median").fit(observations, fold)


def test_preprocessor_rechecks_leakage_and_rejects_refitting(observations):
    fold = grouped_folds(observations, n_splits=3)[0]
    with pytest.raises(SourceLeakageError):
        TrainingOnlyPreprocessor().fit(observations, replace(fold, train=fold.train + (fold.test[0],)))
    p = TrainingOnlyPreprocessor().fit(observations, fold)
    with pytest.raises(RuntimeError, match="refitting"):
        p.fit(observations, fold)


@pytest.mark.parametrize("representation,width", [("SM", 43), ("RF", 43), ("SEM", 86), ("PM", 5)])
def test_feature_selection_excludes_identity_columns(observations, representation, width):
    fold = grouped_folds(observations, n_splits=3)[0]
    p = TrainingOnlyPreprocessor(representation).fit(observations, fold)
    assert p.transform(observations, partition="test").shape == (len(fold.test), width)
    assert {"source_id", "source_name", "obs_id", "compact_object_class"}.isdisjoint(p.columns)
