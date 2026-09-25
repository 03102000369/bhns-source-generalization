import numpy as np
import pandas as pd

from bhns.experiments.source_balancing import source_weights


def test_total_weight_per_source_is_equal(observations):
    weights = source_weights(observations)
    totals = pd.Series(weights).groupby(observations.source_name).sum()
    np.testing.assert_allclose(totals, totals.iloc[0])
    assert np.isclose(weights.mean(), 1.0)
    assert weights.min() > 0


def test_counts_are_computed_from_supplied_training_rows(observations):
    train = observations.groupby("source_name").head(3).copy()
    np.testing.assert_allclose(source_weights(train), 1.0)
