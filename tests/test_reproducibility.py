from copy import deepcopy
import json
from pathlib import Path
import random

import numpy as np
import pandas as pd
import pytest
import yaml

from bhns.config import config_hash, load_config, validate_config
from bhns.evaluation.grouped_cv import grouped_folds
from bhns.reproducibility import run_record, save_predictions, seed_everything

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("path", [ROOT/'configs'/f'{name}.yaml' for name in
    ('base','grouped_cv','loso','observation_split','permutation','source_identity')], ids=lambda p: p.stem)
def test_foundation_configs_load_with_science_disabled(path):
    config = load_config(path)
    assert config["evaluation"]["primary_unit"] == "source"
    assert not config["experiment"]["scientific_runs_enabled"]


def test_hash_stable_but_changes_with_seed():
    config = load_config(ROOT / "configs/base.yaml")
    assert config_hash(config) == config_hash(dict(reversed(list(config.items()))))
    changed = deepcopy(config)
    changed["seed"] += 1
    assert config_hash(config) != config_hash(changed)


def test_observation_bootstrap_or_science_enabling_is_rejected():
    config = load_config(ROOT / "configs/base.yaml")
    config["evaluation"]["bootstrap_unit"] = "observation"
    with pytest.raises(ValueError, match="units"):
        validate_config(config)
    config = load_config(ROOT / "configs/base.yaml")
    config["experiment"]["scientific_runs_enabled"] = True
    with pytest.raises(ValueError, match="disabled"):
        validate_config(config)


def test_yaml_inheritance_cycle_rejected(tmp_path):
    (tmp_path / "a.yaml").write_text("extends: b.yaml\n")
    (tmp_path / "b.yaml").write_text("extends: a.yaml\n")
    with pytest.raises(ValueError, match="cycle"):
        load_config(tmp_path / "a.yaml")


def test_seed_utilities_repeat():
    seed_everything(71)
    first = (random.random(), np.random.random())
    seed_everything(71)
    assert first == (random.random(), np.random.random())


def _prediction_fixture(frame):
    fold = grouped_folds(frame, n_splits=3)[0]
    result = frame.iloc[list(fold.test)][["source_id", "source_name", "obs_id", "compact_object_class"]].copy()
    result = result.rename(columns={"compact_object_class": "true_class"})
    result["p_BH"], result["p_NS"] = 0.4, 0.6  # Serialization test only; no classifier.
    config = load_config(ROOT / "configs/grouped_cv.yaml")
    metadata = run_record(config, project_root=ROOT, frame=frame, folds=[fold], experiment_name="TEST-ONLY")
    return result, fold, metadata


def test_saved_predictions_have_source_obs_ids_and_full_metadata(observations, tmp_path):
    predictions, fold, metadata = _prediction_fixture(observations)
    path = tmp_path / "predictions.csv"
    save_predictions(predictions, path, frame=observations, fold=fold, metadata=metadata)
    saved = pd.read_csv(path)
    assert {"source_name", "obs_id", "experiment_id", "configuration_hash", "fold_id"} <= set(saved)
    assert set(saved.obs_id) == set(observations.iloc[list(fold.test)].obs_id)
    record = json.loads(path.with_suffix(".json").read_text())
    assert record["split_definition"][0]["test"]["source_ids"]
    assert record["configuration_hash"] == config_hash(record["configuration"])


@pytest.mark.parametrize("column", ["source_name", "obs_id"])
def test_prediction_writer_rejects_missing_identifiers(observations, tmp_path, column):
    predictions, fold, metadata = _prediction_fixture(observations)
    with pytest.raises(ValueError, match="require"):
        save_predictions(predictions.drop(columns=column), tmp_path / "bad.csv",
                         frame=observations, fold=fold, metadata=metadata)
    assert not list(tmp_path.iterdir())


def test_prediction_source_reassignment_is_rejected(observations, tmp_path):
    predictions, fold, metadata = _prediction_fixture(observations)
    predictions["source_name"] = "FALSE ATTRIBUTION"
    with pytest.raises(ValueError, match="attribution"):
        save_predictions(predictions, tmp_path / "bad.csv", frame=observations, fold=fold, metadata=metadata)


def test_prediction_writer_requires_matching_fold(observations, tmp_path):
    predictions, fold, metadata = _prediction_fixture(observations)
    metadata["split_definition"] = []
    with pytest.raises(ValueError, match="absent"):
        save_predictions(predictions, tmp_path / "bad.csv", frame=observations, fold=fold, metadata=metadata)
