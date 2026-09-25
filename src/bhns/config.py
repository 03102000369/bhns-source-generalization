"""Safe YAML inheritance, fixed scientific invariants, stable configuration hashes."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import yaml

from bhns.constants import CLASS_ENCODING, N_SPECTRAL_BINS


def _merge(base, override):
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def load_config(path, _seen=None):
    path = Path(path).resolve()
    seen = set() if _seen is None else set(_seen)
    if path in seen:
        raise ValueError(f"Configuration inheritance cycle at {path}")
    seen.add(path)
    with path.open() as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError("Configuration must be a YAML mapping")
    parent = config.pop("extends", None)
    if parent:
        config = _merge(load_config(path.parent / parent, seen), config)
    validate_config(config)
    return config


def validate_config(config):
    if config.get("classes") != CLASS_ENCODING:
        raise ValueError("Primary class mapping must remain BH=0, NS=1")
    if config.get("data", {}).get("n_spectral_bins") != N_SPECTRAL_BINS:
        raise ValueError("The primary schema requires exactly 43 spectral bins")
    evaluation = config.get("evaluation", {})
    if evaluation.get("primary_unit") != "source" or evaluation.get("bootstrap_unit") != "source":
        raise ValueError("Primary evaluation and bootstrap units must be sources")
    if evaluation.get("inner_split") != "source_disjoint":
        raise ValueError("Inner model-selection validation must be source-disjoint")
    if not isinstance(config.get("seed"), int) or isinstance(config["seed"], bool) or config["seed"] < 0:
        raise ValueError("A nonnegative integer random seed is required")
    if config.get("experiment", {}).get("scientific_runs_enabled") is not False:
        raise ValueError("Scientific runs are disabled in the Gates 0–2 release")
    return config


def config_hash(config):
    payload = json.dumps(config, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()
