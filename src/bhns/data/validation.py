"""Fail-closed validation; no implicit relabeling, alias merging or row dropping."""

import numpy as np
import pandas as pd

from bhns.constants import (
    CLASS_ENCODING, ERROR_COLUMNS, FLUX_COLUMNS, IDENTITY_COLUMNS, PARAMETER_COLUMNS,
)
from bhns.data.schema import REQUIRED_COLUMNS, feature_columns


class DatasetValidationError(ValueError):
    """The input cannot safely enter the primary benchmark."""


def require_text(frame, columns):
    for column in columns:
        if column not in frame:
            raise DatasetValidationError(f"Missing column: {column}")
        values = frame[column]
        if values.isna().any() or not values.map(lambda x: isinstance(x, str)).all():
            raise DatasetValidationError(f"{column} must contain nonmissing strings")
        if values.str.strip().eq("").any() or values.ne(values.str.strip()).any():
            raise DatasetValidationError(f"{column} has blank or padded identifiers; resolve explicitly")


def validate_source_groups(frame):
    """Require a one-to-one canonical source ID/name mapping and one class each.

    Undeclared astronomical aliases cannot be detected from strings alone; the
    acquisition review must reconcile these before accepting the manifest.
    """
    if not frame.columns.is_unique:
        raise DatasetValidationError("Duplicate column names")
    if frame.empty:
        raise DatasetValidationError("No observations available")
    require_text(frame, IDENTITY_COLUMNS)
    if not frame.compact_object_class.isin(CLASS_ENCODING).all():
        raise DatasetValidationError("Only BH and NS labels are allowed")
    for key, value in (("source_id", "source_name"), ("source_name", "source_id"),
                       ("source_id", "compact_object_class"),
                       ("source_name", "compact_object_class")):
        if frame.groupby(key)[value].nunique().gt(1).any():
            raise DatasetValidationError(f"Conflicting {value} for {key}")
    if frame.obs_id.duplicated().any():
        raise DatasetValidationError("Duplicate obs_id; resolve segmented/repeated observations explicitly")


def validate_dataset(frame, *, allow_missing_features=False, representation=None):
    validate_source_groups(frame)
    required = REQUIRED_COLUMNS if representation is None else IDENTITY_COLUMNS + feature_columns(representation)
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise DatasetValidationError(f"Missing required columns: {missing}")
    for prefix, expected in (("flux_", FLUX_COLUMNS), ("err_", ERROR_COLUMNS)):
        actual = {c for c in frame.columns if c.startswith(prefix)}
        if actual and actual != set(expected):
            raise DatasetValidationError(f"{prefix} vectors must contain exactly the 43 canonical bins")
    numeric_columns = [c for c in FLUX_COLUMNS + ERROR_COLUMNS if c in frame]
    numeric_columns += [c for c in PARAMETER_COLUMNS if c in frame]
    for column in numeric_columns:
        if not pd.api.types.is_numeric_dtype(frame[column]) or pd.api.types.is_bool_dtype(frame[column]):
            raise DatasetValidationError(f"Non-numeric feature: {column}")
        values = frame[column].to_numpy(dtype=float, na_value=np.nan)
        if np.isinf(values).any():
            raise DatasetValidationError(f"Infinite feature values in {column}")
        if not allow_missing_features and np.isnan(values).any():
            raise DatasetValidationError(f"Missing feature values in {column}; an explicit policy is required")
        if column in ERROR_COLUMNS and (values < 0).any():
            raise DatasetValidationError(f"Negative uncertainty in {column}")
    # Negative background-subtracted flux and zero errors are reported, not silently removed.
    return dataset_summary(frame)


def dataset_summary(frame):
    """Audit counts, not a substitute for validate_dataset."""
    sources = frame.loc[:, ["source_id", "source_name", "compact_object_class"]].drop_duplicates()
    return {
        "sources": int(len(sources)),
        "BH": int(sources.compact_object_class.eq("BH").sum()),
        "NS": int(sources.compact_object_class.eq("NS").sum()),
        "observations": int(len(frame)),
        "spectral_bins": sum(c in frame for c in FLUX_COLUMNS),
        "errors_available": all(c in frame and frame[c].notna().all() for c in ERROR_COLUMNS),
        "pm_parameters_available": all(c in frame and frame[c].notna().all() for c in PARAMETER_COLUMNS),
        "missing_values": {c: int(n) for c, n in frame.isna().sum().items() if n},
        "duplicate_observations": int(frame.obs_id.duplicated().sum()),
        "observations_per_source": {str(k): int(v) for k, v in frame.groupby("source_name").size().items()},
        "negative_flux_values": int((frame[[c for c in FLUX_COLUMNS if c in frame]] < 0).sum().sum()),
        "zero_error_values": int((frame[[c for c in ERROR_COLUMNS if c in frame]] == 0).sum().sum()),
    }
