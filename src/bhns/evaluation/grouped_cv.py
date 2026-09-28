"""Stratify independent sources, then expand to their observations."""

import numpy as np
from sklearn.model_selection import StratifiedGroupKFold

from bhns.data.validation import validate_dataset
from bhns.evaluation.splits import SplitFeasibilityError, make_fold


def grouped_folds(frame, *, n_splits=5, seed=42, representation=None):
    validate_dataset(frame, allow_missing_features=True, representation=representation)
    sources = frame[["source_name", "compact_object_class"]].drop_duplicates().sort_values("source_name")
    counts = sources.groupby("compact_object_class").size()
    if n_splits < 2 or len(counts) != 2 or counts.min() < n_splits:
        raise SplitFeasibilityError("n_splits requires at least that many independent sources of EACH class")
    splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    folds = []
    # One row per source prevents prolific sources from dominating stratification.
    for number, (_, test_source_idx) in enumerate(splitter.split(
        np.zeros((len(sources), 1)), sources.compact_object_class, groups=sources.source_name
    )):
        test_names = set(sources.iloc[test_source_idx].source_name)
        mask = frame.source_name.isin(test_names).to_numpy()
        if frame.loc[mask, "compact_object_class"].nunique() != 2:
            raise SplitFeasibilityError("StratifiedGroupKFold produced a single-class fold; review n_splits/seed")
        folds.append(make_fold(frame, np.flatnonzero(~mask), np.flatnonzero(mask),
                               mode="grouped", seed=seed, fold_id=f"grouped-{number:02d}", representation=representation))
    return folds
