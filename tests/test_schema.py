import numpy as np
import pandas as pd
import pytest

from bhns.constants import ERROR_COLUMNS, FLUX_COLUMNS, PARAMETER_COLUMNS
from bhns.data.loaders import DataGateBlocked, load_observations
from bhns.data.validation import DatasetValidationError, validate_dataset


def test_valid_canonical_table(observations):
    summary = validate_dataset(observations)
    assert summary["sources"] == 12
    assert summary["BH"] == summary["NS"] == 6
    assert summary["spectral_bins"] == 43


@pytest.mark.parametrize("column,value", [("source_id", None), ("source_name", ""),
    ("obs_id", " padded "), ("compact_object_class", None), ("compact_object_class", "WD"),
    ("flux_00", np.inf), ("err_00", -1.0), ("flux_42", np.nan)])
def test_bad_values_rejected(observations, column, value):
    observations.loc[0, column] = value
    with pytest.raises(DatasetValidationError):
        validate_dataset(observations)


@pytest.mark.parametrize("column", ["flux_00", "flux_42", "err_00", "err_42"])
def test_missing_bin_rejected(observations, column):
    with pytest.raises(DatasetValidationError, match="Missing required"):
        validate_dataset(observations.drop(columns=column))


@pytest.mark.parametrize("column", ["flux_43", "err_43", "flux_0"])
def test_extra_bin_rejected(observations, column):
    observations[column] = 0.0
    with pytest.raises(DatasetValidationError, match="exactly"):
        validate_dataset(observations)


def test_duplicate_observation_rejected(observations):
    observations.loc[1, "obs_id"] = observations.loc[0, "obs_id"]
    with pytest.raises(DatasetValidationError, match="Duplicate obs_id"):
        validate_dataset(observations)


def test_missing_requires_explicit_policy(observations):
    observations.loc[0, "flux_00"] = np.nan
    report = validate_dataset(observations, allow_missing_features=True)
    assert report["missing_values"] == {"flux_00": 1}
    observations.loc[1, "flux_00"] = np.inf
    with pytest.raises(DatasetValidationError, match="Infinite"):
        validate_dataset(observations, allow_missing_features=True)


def test_errors_required_pm_optional(observations):
    assert not validate_dataset(observations.drop(columns=list(PARAMETER_COLUMNS)))["pm_parameters_available"]
    with pytest.raises(DatasetValidationError):
        validate_dataset(observations.drop(columns=list(ERROR_COLUMNS)))


def test_csv_roundtrip_preserves_leading_zero_ids(observations, tmp_path):
    observations["obs_id"] = [f"{i:06d}" for i in range(len(observations))]
    path = tmp_path / "observations.csv"
    observations.to_csv(path, index=False)
    loaded = load_observations(path)
    assert loaded.obs_id.tolist() == observations.obs_id.tolist()
    assert loaded[list(FLUX_COLUMNS)].shape[1] == 43


def test_csv_duplicate_header_is_not_mangled(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("source_id,source_id\na,b\n")
    with pytest.raises(DatasetValidationError, match="Duplicate CSV"):
        load_observations(path)


def test_absent_data_does_not_create_anything(tmp_path):
    with pytest.raises(DataGateBlocked):
        load_observations(tmp_path / "absent.csv")
    assert list(tmp_path.iterdir()) == []


def test_no_implicit_numeric_coercion(observations):
    observations["flux_00"] = "invalid"
    with pytest.raises(DatasetValidationError, match="Non-numeric"):
        validate_dataset(observations)
