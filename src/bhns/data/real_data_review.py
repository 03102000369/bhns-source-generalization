"""Data-bound leakage feasibility audit, never a model experiment or prediction."""

from pathlib import Path

import numpy as np

from bhns.data.gate1 import DEFAULT_INPUTS, run_gate1
from bhns.data.loaders import load_observations
from bhns.data.preprocessing import TrainingOnlyPreprocessor
from bhns.evaluation.grouped_cv import grouped_folds
from bhns.evaluation.loso import loso_folds
from bhns.evaluation.observation_split import observation_split
from bhns.evaluation.splits import add_inner_validation, fold_definition, SplitFeasibilityError
from bhns.experiments.source_balancing import source_weights
from bhns.experiments.source_permutation import permute_source_labels
from bhns.reproducibility import run_record, write_json


def inspect_real_structure(frame, config):
    """Exercise configured fold/preprocessing contracts on admitted rows only.

    This does not select hyperparameters, score predictors, fabricate prediction
    records or make source-randomization scientific claims.
    """
    family = config["data"].get("feature_representation", "SM")
    seed = config["seed"]
    evaluation = config.get("evaluation", {})
    folds = [observation_split(frame, test_size=evaluation.get("test_size", .2), seed=seed, representation=family)]
    folds += grouped_folds(frame, n_splits=evaluation.get("n_splits", 5), seed=seed, representation=family)
    folds += loso_folds(frame, seed=seed, representation=family)
    records = []
    for outer in folds:
        fold = add_inner_validation(frame, outer, validation_fraction=evaluation.get("validation_fraction", .2))
        prep = TrainingOnlyPreprocessor(family, seed=seed, **config.get("preprocessing", {})).fit(frame, fold)
        training = frame.iloc[list(fold.train)]
        if prep.fit_obs_ids_ != tuple(training.obs_id):
            raise ValueError("Preprocessing fit observation attribution mismatch")
        for partition in ("train", "validation", "test"):
            if not np.isfinite(prep.transform(frame, partition=partition)).all():
                raise ValueError("Non-finite transformed features")
        weights = source_weights(training)
        totals = training.assign(weight=weights).groupby("source_id").weight.sum().to_numpy()
        if not np.allclose(totals, totals[0]):
            raise ValueError("Unequal total training weight per source")
        record = fold_definition(frame, fold)
        record.update(preprocessing_fit_obs_ids=list(prep.fit_obs_ids_),
                      preprocessing_fit_source_ids=list(prep.fit_source_ids_),
                      feature_columns=list(prep.columns), equal_source_weights="PASS")
        records.append(record)
    original = frame.compact_object_class.copy()
    permutation_checks = []
    for permutation_seed in [seed, seed + 1, seed + 2]:
        labels, mapping = permute_source_labels(frame, seed=permutation_seed)
        if frame.assign(randomized=labels).groupby("source_id").randomized.nunique().ne(1).any():
            raise ValueError("Randomized labels vary within a source")
        expected = frame[["source_id", "compact_object_class"]].drop_duplicates().compact_object_class.value_counts()
        if list(mapping.values()).count(0) != expected.get("BH", 0) or list(mapping.values()).count(1) != expected.get("NS", 0):
            raise ValueError("Randomization changed source-level class counts")
        permutation_checks.append({"seed": permutation_seed, "source_count": len(mapping), "status": "PASS"})
    if not original.equals(frame.compact_object_class):
        raise ValueError("Randomization overwrote true labels")
    return {"folds": records, "randomization_integrity_checks": permutation_checks,
            "prediction_attribution": "Fold test ObsIDs/source IDs preserved; serialization tested only in software until real predictions exist",
            "models_trained": 0, "predictions_generated": 0}


def run_real_data_review(root, config, *, software_pass):
    root = Path(root)
    # Recompute admission instead of trusting a stale PASS report.
    gate1 = run_gate1(root, config)
    record = run_record(config, project_root=root, experiment_name="gates0-2-real-data-review")
    record.update(record_kind="real_data_structure_review", status="BLOCKED", gate1_status=gate1["status"],
                  scientific_experiments_run=False, checks=None, problems=[], gate3_enabled=False)
    if not software_pass:
        record.update(status="FAIL", problems=["Environment/software checks did not pass"])
    elif gate1["status"] != "PASS":
        record["problems"] = ["Gate 1 has no accepted observational cohort; all real-data fold, preprocessing, weighting and randomization checks remain NOT RUN"]
    else:
        try:
            path = root / config["data"].get("observation_table", DEFAULT_INPUTS["observation_table"])
            frame = load_observations(path, representation=config["data"].get("feature_representation", "SM"))
            record["checks"] = inspect_real_structure(frame, config)
            record["status"] = "PASS"
        except SplitFeasibilityError as exc:
            record["problems"] = [f"Admitted cohort cannot support the configured independent-source design: {exc}"]
        except (ValueError, OSError, KeyError) as exc:
            record.update(status="FAIL", problems=[str(exc)])
    write_json(root / "reports/gates_0_2_real_data_review.json", record)
    (root / "reports/gates_0_2_real_data_review.md").write_text(
        "# Gates 0–2 on real data\n\n"
        f"Status: **{record['status']}**. UTC: {record['timestamp_utc']}\n\n"
        f"Fresh Gate 1: {gate1['status']}. Software/environment checks passed: {software_pass}.\n\n"
        + "\n".join(f"- {p}" for p in record["problems"])
        + "\n\nWhen admission passes, this runner exercises observation/grouped/LOSO splits, inner source isolation, "
        "fold-bound training-only preprocessing, attribution and equal-source weights, and source-label permutation integrity. "
        "It records actual partitions and fitting rows without training models or generating predictions. "
        "An infeasible source count blocks the review; no weaker split is substituted.\n\n"
        "Prediction serialization currently has software-fixture coverage only. Real prediction attribution must be rechecked "
        "when experiments produce predictions. Passing this review is not a frozen scientific protocol or a model-performance result.\n\n"
        "Gate 3 remains disabled in this release. No protocol was frozen while the cohort is blocked. "
        "See [machine-readable checks](gates_0_2_real_data_review.json), [Gate 1](gate1_data_report.md), "
        "[software output](test_output.txt), and [decision log](decision_log.md).\n")
    return gate1, record
