"""Exactly one unseen astrophysical source in each outer test fold."""

import numpy as np

from bhns.data.validation import validate_dataset
from bhns.evaluation.splits import make_fold


def loso_folds(frame, *, seed=42, representation=None):
    validate_dataset(frame, allow_missing_features=True, representation=representation)
    folds = []
    for number, name in enumerate(sorted(frame.source_name.unique())):
        mask = frame.source_name.eq(name).to_numpy()
        folds.append(make_fold(frame, np.flatnonzero(~mask), np.flatnonzero(mask),
                               mode="loso", seed=seed, fold_id=f"loso-{number:03d}", representation=representation))
    return folds
