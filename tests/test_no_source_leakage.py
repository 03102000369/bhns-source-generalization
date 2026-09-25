from dataclasses import replace

import pytest

from bhns.evaluation.grouped_cv import grouped_folds
from bhns.evaluation.loso import loso_folds
from bhns.evaluation.observation_split import observation_split
from bhns.evaluation.splits import (
    SourceLeakageError, SplitFeasibilityError, add_inner_validation,
    assert_no_source_leakage, fold_definition, validate_fold,
)


@pytest.mark.parametrize("seed", [0, 42, 71])
def test_grouped_has_zero_source_overlap_and_complete_coverage(observations, seed):
    folds = grouped_folds(observations, n_splits=3, seed=seed)
    seen = []
    for fold in folds:
        train, test = observations.iloc[list(fold.train)], observations.iloc[list(fold.test)]
        assert_no_source_leakage(train, test)
        assert train.compact_object_class.nunique() == test.compact_object_class.nunique() == 2
        seen.extend(fold.test)
    assert sorted(seen) == list(range(len(observations)))


def test_observation_split_deliberately_allows_source_overlap(observations):
    fold = observation_split(observations, seed=42)
    train, test = observations.iloc[list(fold.train)], observations.iloc[list(fold.test)]
    assert set(train.source_name) & set(test.source_name)
    assert set(train.obs_id).isdisjoint(test.obs_id)
    with pytest.raises(SourceLeakageError):
        assert_no_source_leakage(train, test)
    assert fold_definition(observations, fold)["outer_source_overlap"]


def test_loso_exactly_one_source_once_each(observations):
    folds = loso_folds(observations)
    names = []
    for fold in folds:
        test = observations.iloc[list(fold.test)]
        assert test.source_name.nunique() == 1
        assert_no_source_leakage(observations.iloc[list(fold.train)], test)
        names.append(test.source_name.iloc[0])
    assert len(folds) == observations.source_name.nunique()
    assert sorted(names) == sorted(observations.source_name.unique())


@pytest.mark.parametrize("kind", ["grouped", "loso"])
def test_outer_test_sources_never_enter_early_stopping(observations, kind):
    outer = grouped_folds(observations, n_splits=3)[0] if kind == "grouped" else loso_folds(observations)[0]
    inner = add_inner_validation(observations, outer, validation_fraction=0.3)
    validation = observations.iloc[list(inner.validation)]
    test = observations.iloc[list(inner.test)]
    assert_no_source_leakage(validation, test)
    assert_no_source_leakage(observations.iloc[list(inner.train)], validation)
    assert set(inner.train) | set(inner.validation) == set(outer.train)
    assert inner.test == outer.test


def test_duplicate_or_cross_partition_rows_fail(observations):
    fold = grouped_folds(observations, n_splits=3)[0]
    broken = replace(fold, train=fold.train + (fold.test[0],))
    with pytest.raises(SourceLeakageError):
        validate_fold(observations, broken)


def test_forged_grouped_mode_fails(observations):
    fold = observation_split(observations)
    with pytest.raises(SourceLeakageError, match="leakage"):
        validate_fold(observations, replace(fold, mode="grouped"))


def test_validation_source_injection_fails(observations):
    fold = grouped_folds(observations, n_splits=3)[0]
    # Even with disjoint row numbers, one test-source row in validation is forbidden.
    broken = replace(fold, validation=(fold.test[0],), test=fold.test[1:])
    with pytest.raises((SourceLeakageError, SplitFeasibilityError)):
        validate_fold(observations, broken)


def test_dataset_reordering_invalidates_fold(observations):
    fold = grouped_folds(observations, n_splits=3)[0]
    with pytest.raises(SourceLeakageError, match="changed/reordered"):
        validate_fold(observations.iloc[::-1], fold)


def test_split_reproducibility(observations):
    assert grouped_folds(observations, n_splits=3) == grouped_folds(observations, n_splits=3)
    assert observation_split(observations, seed=42) != observation_split(observations, seed=43)


def test_infeasible_group_count_fails_instead_of_using_observations(observations):
    with pytest.raises(SplitFeasibilityError):
        grouped_folds(observations, n_splits=7)


def test_infeasible_inner_split_fails(observations):
    small = observations[observations.source_name.isin([f"TEST SOURCE {i:02d}" for i in range(4)])].reset_index(drop=True)
    outer = loso_folds(small)[0]
    with pytest.raises(SplitFeasibilityError):
        add_inner_validation(small, outer)


def test_inner_seed_is_recorded_separately(observations):
    outer = grouped_folds(observations, n_splits=3, seed=42)[0]
    inner = add_inner_validation(observations, outer, validation_fraction=0.3, seed=71)
    saved = fold_definition(observations, inner)
    assert saved["seed"] == 42
    assert saved["validation_seed"] == 71
    assert saved["validation_fraction"] == 0.3
    assert inner == add_inner_validation(observations, outer, validation_fraction=0.3, seed=71)
