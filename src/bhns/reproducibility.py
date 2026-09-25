"""Seeds, logging and machine-readable records; no model execution."""

from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import logging
from pathlib import Path
import platform
import random
import subprocess

import numpy as np

from bhns.config import config_hash
from bhns.evaluation.splits import fold_definition, validate_fold

PACKAGES = ("numpy", "pandas", "scipy", "matplotlib", "scikit-learn", "torch",
            "PyYAML", "joblib", "pytest", "tqdm")


def configure_logging():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def seed_everything(seed, *, include_torch=False):
    random.seed(seed)
    np.random.seed(seed)
    if include_torch:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        torch.use_deterministic_algorithms(True)
        torch.backends.cudnn.benchmark = False
    # PYTHONHASHSEED must be set before interpreter startup; do not pretend
    # setting it here controls an already-running interpreter's hash seed.


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def environment_record():
    versions = {}
    for package in PACKAGES:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    optional = {}
    for package in ("astropy", "astropy-iers-data", "pyerfa", "pyarrow", "h5py"):
        try:
            optional[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            optional[package] = None
    return {"python": platform.python_version(), "platform": platform.platform(),
            "packages": versions, "optional_packages": optional}


def run_record(config, *, project_root, experiment_name=None, folds=None, frame=None):
    root = Path(project_root).resolve()
    def git(*args):
        try:
            result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=10)
            return result.stdout.strip() if result.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired):
            return None
    timestamp = datetime.now(timezone.utc).isoformat()
    digest = config_hash(config)
    name = experiment_name or config["experiment"]["name"]
    files = sorted([*root.glob("src/**/*.py"), *root.glob("scripts/*.py"), *root.glob("configs/*.yaml"),
                    *root.glob("tests/*.py"), *root.glob("pyproject.toml"), *root.glob("requirements*.txt")])
    checksums = {str(p.relative_to(root)): file_sha256(p) for p in files}
    return {
        "experiment_id": f"{name}-{timestamp.replace(':', '').replace('+', '_')}-{digest[:12]}",
        "configuration_hash": digest, "configuration": config, "random_seed": config["seed"],
        "git_commit": git("rev-parse", "HEAD"), "git_status": git("status", "--porcelain", "--", "."),
        "timestamp_utc": timestamp, "model_type": config["experiment"].get("model"),
        "record_kind": "software_foundation_only", "environment": environment_record(),
        "code_checksums": checksums,
        "split_definition": [fold_definition(frame, f) for f in folds] if folds is not None else [],
        "metrics": None,
    }


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def save_predictions(predictions, path, *, frame, fold, metadata):
    """Future observation predictions cannot lose their source/ObsID attribution.

    This serialization contract is unit-tested with artificial probabilities in
    pytest temporary directories only. No scientific predictions exist yet.
    """
    validate_fold(frame, fold)
    required = {"source_id", "source_name", "obs_id", "true_class", "p_BH", "p_NS"}
    if required - set(predictions) or predictions.empty:
        raise ValueError("Predictions require source_name, source_id, obs_id, true_class, p_BH and p_NS")
    if predictions.obs_id.duplicated().any():
        raise ValueError("Save one prediction per test observation per fold")
    expected = frame.iloc[list(fold.test)].set_index("obs_id").sort_index()
    actual = predictions.set_index("obs_id").sort_index()
    if set(actual.index) != set(expected.index):
        raise ValueError("Predictions must cover exactly the test observations")
    for left, right in (("source_id", "source_id"), ("source_name", "source_name"),
                        ("true_class", "compact_object_class")):
        if not actual[left].eq(expected[right]).all():
            raise ValueError(f"Prediction attribution mismatch: {left}")
    probabilities = actual[["p_BH", "p_NS"]].to_numpy(dtype=float)
    if (not np.isfinite(probabilities).all() or (probabilities < 0).any()
            or (probabilities > 1).any() or not np.allclose(probabilities.sum(axis=1), 1)):
        raise ValueError("Invalid class probabilities")
    if not {"experiment_id", "configuration_hash", "configuration", "random_seed",
            "timestamp_utc", "git_commit", "model_type", "split_definition", "metrics"} <= metadata.keys():
        raise ValueError("Incomplete reproducibility metadata")
    if metadata["configuration_hash"] != config_hash(metadata["configuration"]):
        raise ValueError("Configuration hash does not match stored configuration")
    if fold_definition(frame, fold) not in metadata["split_definition"]:
        raise ValueError("Prediction fold is absent from metadata")
    path = Path(path)
    if path.exists() or path.with_suffix(".json").exists():
        raise FileExistsError("Do not overwrite an existing prediction artifact")
    path.parent.mkdir(parents=True, exist_ok=True)
    saved = predictions.copy()
    saved["experiment_id"] = metadata["experiment_id"]
    saved["configuration_hash"] = metadata["configuration_hash"]
    saved["fold_id"] = fold.fold_id
    saved.to_csv(path, index=False)
    write_json(path.with_suffix(".json"), metadata)
