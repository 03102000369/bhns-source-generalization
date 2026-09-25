"""Gate 2 weighting utility only; no training comparison is run."""

import numpy as np

from bhns.data.validation import validate_source_groups


def source_weights(training_frame):
    """Pass TRAINING rows only; mean-one weights give equal total weight/source."""
    validate_source_groups(training_frame)
    counts = training_frame.groupby("source_name").source_name.transform("size").to_numpy()
    weights = 1.0 / counts
    return weights / np.mean(weights)
