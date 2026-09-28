"""Gate 2 label-integrity utility only; no permutation experiment runner."""

import numpy as np
import pandas as pd

from bhns.constants import CLASS_ENCODING
from bhns.data.validation import validate_source_groups


def permute_source_labels(frame, *, seed):
    """Shuffle labels across SOURCES, preserving their original class counts.

    Observation class balance need not be preserved when source sizes differ.
    Never overwrite compact_object_class: the returned fake target is separate.
    Independent seeds can legitimately yield the same finite permutation; do
    not reject the identity assignment and thereby bias the randomization null.
    """
    validate_source_groups(frame)
    sources = frame[["source_name", "compact_object_class"]].drop_duplicates().sort_values("source_name")
    original = sources.compact_object_class.map(CLASS_ENCODING).to_numpy()
    shuffled = np.random.default_rng(seed).permutation(original)
    mapping = dict(zip(sources.source_name, map(int, shuffled)))
    return pd.Series(frame.source_name.map(mapping), index=frame.index, name="randomized_label"), mapping
