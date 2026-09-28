"""SYNTHETIC fixture checks for alternate feature families and review boundaries."""

import pytest

from bhns.constants import IDENTITY_COLUMNS
from bhns.data.real_data_review import inspect_real_structure, run_real_data_review
from bhns.data.schema import feature_columns


@pytest.mark.parametrize("family", ["SM", "PM", "COMBINED"])
def test_all_families_retain_source_disjoint_inner_and_outer_folds(observations, family):
    frame = observations[list(IDENTITY_COLUMNS + feature_columns(family))].copy()
    config = {"seed": 42, "data": {"feature_representation": family},
              "evaluation": {"n_splits": 3, "validation_fraction": .3},
              "preprocessing": {"standardize": True, "imputation": "median", "pca_components": 2}}
    record = inspect_real_structure(frame, config)
    assert len(record["folds"]) == 16
    assert record["predictions_generated"] == record["models_trained"] == 0
    for fold in record["folds"]:
        if fold["mode"] != "observation":
            assert fold["outer_source_overlap"] == []
        assert set(fold["preprocessing_fit_source_ids"]) == set(fold["train"]["source_ids"])
        assert not set(fold["train"]["source_ids"]) & set(fold["validation"]["source_ids"])
        assert not set(fold["preprocessing_fit_obs_ids"]) & set(fold["test"]["obs_ids"])


def test_real_review_does_not_trust_stale_gate_report(tmp_path):
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports/gate1_data_report.json").write_text('{"status":"PASS"}')
    gate, review = run_real_data_review(tmp_path, {"seed": 42, "data": {}, "experiment": {"name": "SYNTHETIC"}}, software_pass=True)
    assert gate["status"] == review["status"] == "BLOCKED"
    assert review["checks"] is None and not review["gate3_enabled"]
