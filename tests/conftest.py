"""Artificial arithmetic arrays for SOFTWARE TESTS ONLY, never observational data.

These fixtures stay in memory/pytest temp directories. They do not simulate RXTE
physics and must never be written to project data/ or reported as science.
"""

import numpy as np
import pandas as pd
import pytest

from bhns.constants import ERROR_COLUMNS, FLUX_COLUMNS, PARAMETER_COLUMNS


@pytest.fixture
def observations():
    source = np.repeat(np.arange(12), np.arange(12, 24))
    rows = np.arange(len(source))
    frame = pd.DataFrame({
        "source_id": [f"test-id-{i:02d}" for i in source],
        "source_name": [f"TEST SOURCE {i:02d}" for i in source],
        "compact_object_class": np.where(source % 2 == 0, "BH", "NS"),
        "obs_id": [f"test-obs-{i:04d}" for i in rows],
    })
    features = {
        c: (rows.astype(float) * (j + 1) % 37) + source / 10.0
        for j, c in enumerate(FLUX_COLUMNS)
    }
    features.update({c: np.full(len(rows), 0.1) for c in ERROR_COLUMNS})
    features.update({c: rows.astype(float) / (j + 1) for j, c in enumerate(PARAMETER_COLUMNS)})
    return pd.concat([frame, pd.DataFrame(features)], axis=1)


@pytest.fixture
def provenance(observations):
    frame = observations[["source_id", "source_name", "compact_object_class"]].drop_duplicates().copy()
    frame["label_reference"] = "TEST FIXTURE ONLY; not astronomical evidence"
    frame["label_status"] = "verified"
    frame["notes"] = "Unit-test fixture, not a real source"
    return frame
