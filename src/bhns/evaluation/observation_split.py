"""Secondary reference split, deliberately permitting shared sources."""

import numpy as np
from sklearn.model_selection import train_test_split

from bhns.data.validation import validate_dataset
from bhns.evaluation.splits import SplitFeasibilityError, make_fold


def observation_split(frame, *, test_size=0.2, seed=42, representation=None):
    validate_dataset(frame, allow_missing_features=True, representation=representation)
    try:
        train, test = train_test_split(np.arange(len(frame)), test_size=test_size,
                                       stratify=frame.compact_object_class, random_state=seed)
    except ValueError as exc:
        raise SplitFeasibilityError(f"Infeasible observation split: {exc}") from exc
    return make_fold(frame, train, test, mode="observation", seed=seed, fold_id="observation", representation=representation)
