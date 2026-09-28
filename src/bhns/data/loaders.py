"""Canonical CSV/Parquet loader. Never guesses legacy column names or labels."""

import csv
from pathlib import Path

import pandas as pd

from bhns.constants import IDENTITY_COLUMNS
from bhns.data.validation import DatasetValidationError, validate_dataset


class DataGateBlocked(FileNotFoundError):
    """Verified canonical observations have not been supplied."""


def read_table(path):
    path = Path(path)
    if not path.is_file():
        raise DataGateBlocked(f"Missing data file: {path}. See data/README.md and acquisition_checklist.md")
    if path.suffix.lower() == ".csv":
        # pandas otherwise mangles duplicate headers, hiding malformed input.
        with path.open(newline="", encoding="utf-8-sig") as handle:
            header = next(csv.reader(handle), [])
        if len(header) != len(set(header)):
            raise DatasetValidationError("Duplicate CSV column names")
        strings = {c: "string" for c in IDENTITY_COLUMNS if c in header}
        return pd.read_csv(path, dtype=strings)
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)  # Optional pyarrow extra required.
    raise DatasetValidationError("Use canonical .csv or .parquet; raw FITS needs reviewed reduction first")


def load_observations(path, *, manifest_path=None, allow_missing_features=False, representation=None):
    frame = read_table(path)
    validate_dataset(frame, allow_missing_features=allow_missing_features, representation=representation)
    if manifest_path is not None:
        from bhns.data.source_manifest import validate_manifest
        validate_manifest(frame, read_table(manifest_path))
    return frame.reset_index(drop=True)
