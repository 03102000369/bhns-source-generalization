"""Immutable positional folds bound to the exact table; explicit leakage failures."""

from dataclasses import dataclass, replace
import hashlib
import json

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from bhns.data.validation import validate_dataset


class SourceLeakageError(ValueError):
    """An observation or physical source crossed a forbidden split boundary."""


class SplitFeasibilityError(ValueError):
    """Too few independent sources/classes to construct the requested split."""


def dataset_fingerprint(frame):
    digest = hashlib.sha256()
    digest.update(json.dumps([(c, str(t)) for c, t in frame.dtypes.items()]).encode())
    digest.update(pd.util.hash_pandas_object(frame, index=False).to_numpy().tobytes())
    return digest.hexdigest()


@dataclass(frozen=True)
class Fold:
    train: tuple[int, ...]
    test: tuple[int, ...]
    mode: str
    seed: int
    fold_id: str
    dataset_fingerprint: str
    validation: tuple[int, ...] = ()
    validation_seed: int | None = None
    validation_fraction: float | None = None
    representation: str | None = None


def assert_no_source_leakage(train, test):
    """Exception-based check remains active under python -O."""
    for column in ("source_name", "source_id"):
        overlap = set(train[column]) & set(test[column])
        if overlap:
            raise SourceLeakageError(f"{column} leakage: {sorted(overlap)}")
    overlap = set(train.obs_id) & set(test.obs_id)
    if overlap:
        raise SourceLeakageError(f"Observation leakage: {sorted(overlap)}")


def validate_fold(frame, fold):
    validate_dataset(frame, allow_missing_features=True, representation=fold.representation)
    if fold.mode not in {"observation", "grouped", "loso"}:
        raise ValueError(f"Unknown fold mode: {fold.mode}")
    if dataset_fingerprint(frame) != fold.dataset_fingerprint:
        raise SourceLeakageError("Dataset changed/reordered since split construction")
    partitions = {"train": fold.train, "test": fold.test, "validation": fold.validation}
    if not fold.train or not fold.test:
        raise SplitFeasibilityError("Train and test partitions must be nonempty")
    combined = []
    for name, positions in partitions.items():
        if any(not isinstance(i, (int, np.integer)) or isinstance(i, bool) for i in positions):
            raise SourceLeakageError(f"{name} indices must be integer positions")
        if len(positions) != len(set(positions)):
            raise SourceLeakageError(f"Repeated positions in {name}")
        combined.extend(positions)
    if len(combined) != len(set(combined)):
        raise SourceLeakageError("An observation occurs in multiple partitions")
    if set(combined) != set(range(len(frame))):
        raise SourceLeakageError("Partitions must cover the exact input table")
    train, test = frame.iloc[list(fold.train)], frame.iloc[list(fold.test)]
    if train.compact_object_class.nunique() != 2:
        raise SplitFeasibilityError("Training must include independent BH and NS sources")
    if fold.mode != "observation":
        assert_no_source_leakage(train, test)
    if fold.mode == "loso" and test.source_name.nunique() != 1:
        raise SourceLeakageError("LOSO must hold out exactly one source")
    if fold.validation:
        validation = frame.iloc[list(fold.validation)]
        assert_no_source_leakage(train, validation)
        if validation.compact_object_class.nunique() != 2:
            raise SplitFeasibilityError("Inner validation must contain both classes")
        if fold.mode != "observation":
            assert_no_source_leakage(validation, test)
    return fold


def make_fold(frame, train, test, *, mode, seed, fold_id, representation=None):
    fold = Fold(tuple(sorted(map(int, train))), tuple(sorted(map(int, test))),
                mode, seed, str(fold_id), dataset_fingerprint(frame), representation=representation)
    return validate_fold(frame, fold)


def add_inner_validation(frame, outer_fold, *, validation_fraction=0.2, seed=None):
    """Split only outer-training sources for model selection/early stopping.

    The outer test is never a candidate for validation. Inner validation is
    source-disjoint even in the observation-wise diagnostic. For that diagnostic
    only, outer test sources may intentionally overlap either inner partition.
    """
    validate_fold(frame, outer_fold)
    if outer_fold.validation:
        raise ValueError("This fold already has inner validation")
    if not 0 < validation_fraction < 1:
        raise ValueError("validation_fraction must lie strictly between zero and one")
    seed = outer_fold.seed if seed is None else seed
    candidates = frame.iloc[list(outer_fold.train)]
    sources = candidates[["source_name", "compact_object_class"]].drop_duplicates().sort_values("source_name")
    if sources.groupby("compact_object_class").size().min() < 2:
        raise SplitFeasibilityError("Inner source-disjoint validation needs at least two training sources per class")
    try:
        train_names, validation_names = train_test_split(
            sources.source_name.to_numpy(), test_size=validation_fraction,
            stratify=sources.compact_object_class.to_numpy(), random_state=seed,
        )
    except ValueError as exc:
        raise SplitFeasibilityError(f"Infeasible inner source split: {exc}") from exc
    train_set, validation_set = set(train_names), set(validation_names)
    train = tuple(i for i in outer_fold.train if frame.iloc[i].source_name in train_set)
    validation = tuple(i for i in outer_fold.train if frame.iloc[i].source_name in validation_set)
    return validate_fold(frame, replace(outer_fold, train=train, validation=validation,
                                        validation_seed=seed, validation_fraction=validation_fraction))


def fold_definition(frame, fold):
    """Persist source IDs AND obs IDs so every partition can be reconstructed."""
    validate_fold(frame, fold)
    result = {"mode": fold.mode, "seed": fold.seed, "fold_id": fold.fold_id,
              "dataset_fingerprint": fold.dataset_fingerprint,
              "validation_seed": fold.validation_seed, "validation_fraction": fold.validation_fraction,
              "representation": fold.representation}
    for name in ("train", "validation", "test"):
        positions = getattr(fold, name)
        rows = frame.iloc[list(positions)]
        result[name] = {
            "positions": list(positions), "obs_ids": rows.obs_id.tolist(),
            "source_ids": sorted(rows.source_id.unique().tolist()),
            "source_names": sorted(rows.source_name.unique().tolist()),
        }
    result["outer_source_overlap"] = sorted(
        set(result["train"]["source_names"] + result["validation"]["source_names"])
        & set(result["test"]["source_names"])
    )
    return result
