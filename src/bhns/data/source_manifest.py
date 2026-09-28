"""Observed source census joined to explicit, externally reviewed label evidence."""

from pathlib import Path

import pandas as pd

from bhns.constants import MANIFEST_COLUMNS, PROVENANCE_COLUMNS
from bhns.data.validation import DatasetValidationError, require_text, validate_source_groups


def empty_manifest():
    """Header only: no invented 61-source roster or label evidence."""
    return pd.DataFrame(columns=MANIFEST_COLUMNS)


def build_source_manifest(observations, provenance):
    validate_source_groups(observations)
    if not provenance.columns.is_unique or set(PROVENANCE_COLUMNS) - set(provenance):
        raise DatasetValidationError("Incomplete or duplicated label provenance columns")
    require_text(provenance, [c for c in PROVENANCE_COLUMNS if c != "notes"])
    if provenance.source_id.duplicated().any() or provenance.source_name.duplicated().any():
        raise DatasetValidationError("Provenance requires exactly one row per canonical source")
    if not provenance.label_status.isin(["verified", "pending", "disputed"]).all():
        raise DatasetValidationError("Label status must be verified, pending or disputed")
    census = observations.groupby(
        ["source_id", "source_name", "compact_object_class"], sort=True
    ).size().rename("n_observations").reset_index()
    if set(census.source_id) != set(provenance.source_id):
        raise DatasetValidationError("Provenance must cover exactly the observed source IDs")
    for column in ("source_name", "compact_object_class"):
        left = census.set_index("source_id")[column].sort_index()
        right = provenance.set_index("source_id")[column].sort_index()
        if not left.eq(right).all():
            raise DatasetValidationError(f"Provenance {column} disagrees with observations; no automatic correction")
    result = census.merge(provenance, on=["source_id", "source_name", "compact_object_class"],
                          how="left", validate="one_to_one")
    return result.loc[:, list(MANIFEST_COLUMNS)]


def validate_manifest(observations, manifest, *, require_verified=True):
    if set(MANIFEST_COLUMNS) - set(manifest):
        raise DatasetValidationError("Source manifest is incomplete")
    expected = build_source_manifest(observations, manifest[list(PROVENANCE_COLUMNS)])
    actual = manifest.set_index("source_id").sort_index()
    expected = expected.set_index("source_id").sort_index()
    if not actual.n_observations.eq(expected.n_observations).all():
        raise DatasetValidationError("Manifest observation counts do not match observations")
    if require_verified and not actual.label_status.eq("verified").all():
        raise DatasetValidationError("Pending/disputed labels block Gate 1; retain them for review")
    return expected.reset_index()


def save_manifest(manifest, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest.to_csv(path, index=False)
