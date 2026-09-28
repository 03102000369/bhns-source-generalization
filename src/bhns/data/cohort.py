"""Scientific cohort acceptance above the backwards-compatible structural loader."""

import hashlib
from pathlib import Path
import re

import numpy as np
import pandas as pd

from bhns.constants import ERROR_COLUMNS, FLUX_COLUMNS, PARAMETER_COLUMNS
from bhns.data.aliases import AliasResolver
from bhns.data.spectral_products import inspect_product
from bhns.data.validation import DatasetValidationError, require_text, validate_dataset
from bhns.reproducibility import file_sha256

OBSERVATION_MANIFEST_COLUMNS = (
    "observation_id", "rxte_obsid", "source_id", "canonical_source", "raw_source_name",
    "class_label", "observation_time", "instrument", "data_product",
    "spectrum_path_or_reference", "error_path_or_reference", "energy_grid_id",
    "feature_record_id", "provenance_record_id", "usable", "exclusion_reason",
)
PRODUCT_PROVENANCE_COLUMNS = (
    "provenance_record_id", "observation_id", "rxte_obsid", "source_id", "status",
    "original_location", "raw_path", "raw_sha256", "product_path", "product_sha256",
    "acquisition_date", "preprocessing_method", "feature_extraction_version",
    "source_mapping_reference", "source_mapping_status", "flux_units", "error_units",
    "error_definition", "zero_error_policy", "zero_error_reason", "energy_grid_id",
    "pm_definition_id", "processing_log_path", "processing_log_sha256",
)


def as_bool(value):
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, str) and value.lower() in {"true", "false"}:
        return value.lower() == "true"
    raise DatasetValidationError(f"Expected explicit true/false, got {value!r}")


def valid_rxte_obsid(value):
    # Base directory identifier, optionally followed by the event flag. Syntax
    # alone never establishes existence or resolves coalesced XTEMASTER entries.
    return isinstance(value, str) and re.fullmatch(r"\d{5}-\d{2}-\d{2}-\d{2}[A-Z0-9]?", value) is not None


def _check_file(root, path, checksum):
    if not isinstance(path, str) or not path:
        raise DatasetValidationError("Missing local provenance product path")
    file = (Path(root) / path).resolve()
    if not file.is_file():
        raise DatasetValidationError(f"Missing provenance file: {path}")
    if not re.fullmatch(r"[a-f0-9]{64}", checksum) or file_sha256(file) != checksum:
        raise DatasetValidationError(f"Checksum mismatch: {path}")
    return file


def _reference(reference_id, external, supports):
    if reference_id not in external.index:
        raise DatasetValidationError(f"Missing external evidence: {reference_id}")
    row = external.loc[reference_id]
    if row.get("access_status") != "verified" or not as_bool(row.get(supports, "false")):
        raise DatasetValidationError(f"Reference does not support {supports}: {reference_id}")


def validate_cohort(frame, manifest, registry, aliases, products, external_sources,
                    grids, pm_definitions, *, root, representation="SM"):
    """Return acceptance checks for a nonempty, explicitly selected cohort.

    No rows are silently dropped or relabeled. Unusable manifest entries can be
    retained, but the feature table must match usable entries exactly. Scientific
    review declarations bind to real local files and exact identities/checksums.
    """
    validate_dataset(frame, representation=representation)
    if set(OBSERVATION_MANIFEST_COLUMNS) - set(manifest):
        raise DatasetValidationError("Incomplete observation manifest columns")
    if set(PRODUCT_PROVENANCE_COLUMNS) - set(products):
        raise DatasetValidationError("Incomplete product provenance columns")
    for table, keys in [(manifest, ["observation_id", "rxte_obsid"]),
                        (products, ["provenance_record_id", "observation_id"]),
                        (external_sources, ["reference_id"])]:
        if not table.columns.is_unique:
            raise DatasetValidationError("Duplicate manifest/provenance columns")
        for key in keys:
            if table[key].duplicated().any():
                raise DatasetValidationError(f"Duplicate {key}")
    require_text(manifest, ["observation_id", "rxte_obsid", "raw_source_name", "class_label"])
    if not manifest.rxte_obsid.map(valid_rxte_obsid).all():
        raise DatasetValidationError("Malformed RXTE ObsID")
    if not manifest.class_label.isin(["BH", "NS", "UNRESOLVED"]).all():
        raise DatasetValidationError("Invalid observation label vocabulary")
    usable_mask = manifest.usable.map(as_bool)
    unusable = manifest.loc[~usable_mask]
    if not unusable.empty:
        require_text(unusable, ["exclusion_reason"])
    selected = manifest.loc[usable_mask].copy()
    if selected.empty:
        raise DatasetValidationError("No usable observations")
    require_text(selected, ["source_id", "canonical_source", "feature_record_id", "provenance_record_id", "instrument", "data_product"])
    if selected.feature_record_id.duplicated().any() or selected.provenance_record_id.duplicated().any():
        raise DatasetValidationError("Repeated feature/provenance record for usable observations")
    if set(frame.obs_id) != set(selected.observation_id):
        raise DatasetValidationError("Feature table must equal the usable observation set exactly")
    if selected.class_label.eq("UNRESOLVED").any() or selected.exclusion_reason.fillna("").ne("").any():
        raise DatasetValidationError("Unresolved/excluded observation marked usable")
    resolver = AliasResolver(registry, aliases)
    sources, evidence = registry.set_index("source_id"), external_sources.set_index("reference_id")
    provenance = products.set_index("provenance_record_id")
    features = frame.set_index("obs_id")
    require_spectrum = representation.upper() != "PM"
    require_pm = representation.upper() in {"PM", "COMBINED"}
    require_errors = representation.upper() == "SEM"
    flux_signatures, grid_hashes, error_counts = {}, set(), 0
    pm_ids, feature_versions = set(), set()
    all_file_checksums = {}
    for row in selected.itertuples(index=False):
        resolved = resolver.canonicalize_source_name(row.raw_source_name)
        if resolved.source_id != row.source_id or resolved.canonical_source_name != row.canonical_source:
            raise DatasetValidationError("Alias and canonical source disagree")
        label = sources.loc[row.source_id]
        if label.classification_status != "verified" or label.class_label != row.class_label:
            raise DatasetValidationError("Class label is not supported by verified registry evidence")
        _reference(label.classification_reference, evidence, "supports_classification")
        _reference(resolved.mapping_reference, evidence, "supports_alias")
        feature = features.loc[row.observation_id]
        if (feature.source_id != row.source_id or feature.source_name != row.canonical_source
                or feature.compact_object_class != row.class_label):
            raise DatasetValidationError("Observation-to-feature identity or label mismatch")
        if row.instrument != "RXTE/PCA":
            raise DatasetValidationError("Usable records must be RXTE/PCA products")
        if row.provenance_record_id not in provenance.index:
            raise DatasetValidationError("Missing observation provenance")
        prov = provenance.loc[row.provenance_record_id]
        for key in ("original_location", "acquisition_date", "preprocessing_method", "feature_extraction_version"):
            if not isinstance(prov[key], str) or not prov[key].strip():
                raise DatasetValidationError(f"Missing provenance {key}")
        try:
            if pd.isna(pd.Timestamp(prov.acquisition_date)):
                raise ValueError("Missing acquisition timestamp")
        except (ValueError, TypeError) as exc:
            raise DatasetValidationError("Invalid acquisition date") from exc
        if prov.status != "verified" or prov.source_mapping_status != "verified":
            raise DatasetValidationError("Unresolved observation/product provenance")
        if (prov.observation_id != row.observation_id or prov.rxte_obsid != row.rxte_obsid
                or prov.source_id != row.source_id):
            raise DatasetValidationError("Product provenance identifies a different observation/source")
        _reference(prov.source_mapping_reference, evidence, "supports_observation_mapping")
        for path_key, sha_key in (("raw_path", "raw_sha256"), ("product_path", "product_sha256"),
                                  ("processing_log_path", "processing_log_sha256")):
            _check_file(root, prov[path_key], prov[sha_key])
            all_file_checksums[prov[path_key]] = prov[sha_key]
        feature_versions.add(prov.feature_extraction_version)
        if prov.zero_error_policy == "documented_allow" and not prov.zero_error_reason:
            raise DatasetValidationError("Zero-error allowance lacks scientific justification")
        product = inspect_product(Path(root) / prov.product_path, require_spectrum=require_spectrum,
            require_errors=require_errors, require_pm=require_pm, flux_units=prov.flux_units,
            error_units=prov.error_units, error_definition=prov.error_definition, zero_policy=prov.zero_error_policy)
        if product["grid"] is not None:
            grid = product["grid"]
            if (row.energy_grid_id != prov.energy_grid_id or row.energy_grid_id not in grids
                    or grids[row.energy_grid_id].get("status") != "verified"
                    or grids[row.energy_grid_id].get("grid_sha256") != grid["grid_sha256"]):
                raise DatasetValidationError("Actual spectrum grid does not match reviewed grid evidence")
            grid_evidence = grids[row.energy_grid_id]
            if (grid_evidence.get("nominal_band_keV") != [5, 25]
                    or grid_evidence.get("native_bounds_reviewed") is not True
                    or not grid_evidence.get("review_notes")):
                raise DatasetValidationError("Native grid bounds lack a documented review against the nominal 5–25 keV band")
            _reference(grid_evidence.get("review_reference", ""), evidence, "supports_spectrum")
            if grid["gap_count"]:
                raise DatasetValidationError("Missing/gapped native bins need explicit scientific review")
            grid_hashes.add(grid["grid_sha256"])
            if not prov.flux_units or row.spectrum_path_or_reference != prov.product_path:
                raise DatasetValidationError("Missing/mismatched spectrum location or units")
            if set(FLUX_COLUMNS) <= set(frame) and not np.array_equal(feature[list(FLUX_COLUMNS)].to_numpy(float), product["flux"]):
                raise DatasetValidationError("Canonical flux values disagree with verified product")
            # Duplicate fluxes are a review stop even if ObsIDs or error arrays differ.
            signature = hashlib.sha256(product["flux"].astype("<f8").tobytes() + grid["grid_sha256"].encode()).hexdigest()
            if signature in flux_signatures:
                raise DatasetValidationError(f"Duplicate spectra: {flux_signatures[signature]} and {row.observation_id}")
            flux_signatures[signature] = row.observation_id
            if product["errors"]["available"]:
                error_counts += 1
                if row.error_path_or_reference != prov.product_path:
                    raise DatasetValidationError("Error product attribution mismatch")
                if set(ERROR_COLUMNS) <= set(frame) and not np.array_equal(feature[list(ERROR_COLUMNS)].to_numpy(float), product["error_values"]):
                    raise DatasetValidationError("Canonical errors disagree with original product")
            elif row.error_path_or_reference or set(ERROR_COLUMNS) <= set(frame):
                raise DatasetValidationError("Claimed errors are absent from the numerical product")
        elif set(FLUX_COLUMNS) <= set(frame) or set(ERROR_COLUMNS) <= set(frame):
            raise DatasetValidationError("Feature table claims spectra/errors absent from product")
        if require_pm:
            definition = pm_definitions.get(prov.pm_definition_id, {})
            if definition.get("status") != "verified":
                raise DatasetValidationError("PM definitions are unverified")
            for parameter in PARAMETER_COLUMNS:
                spec = definition.get("parameters", {}).get(parameter, {})
                if any(not spec.get(key) for key in ("definition", "units", "fit_method", "reference")):
                    raise DatasetValidationError(f"Incomplete PM definition: {parameter}")
                _reference(spec["reference"], evidence, "supports_pm_features")
            if not np.array_equal(feature[list(PARAMETER_COLUMNS)].to_numpy(float), product["pm"]):
                raise DatasetValidationError("Canonical PM values disagree with verified product")
            pm_ids.add(prov.pm_definition_id)
    if len(grid_hashes) > 1:
        raise DatasetValidationError("Non-identical native grids; no reviewed alignment/rebinning is implemented")
    if len(pm_ids) > 1 or len(feature_versions) > 1:
        raise DatasetValidationError("Inconsistent PM definitions or extraction versions need a reviewed harmonization")
    unique = selected[["source_id", "class_label"]].drop_duplicates()
    return {
        "observations": len(selected), "unique_sources": len(unique),
        "BH_sources": int(unique.class_label.eq("BH").sum()), "NS_sources": int(unique.class_label.eq("NS").sum()),
        "BH_observations": int(selected.class_label.eq("BH").sum()), "NS_observations": int(selected.class_label.eq("NS").sum()),
        "excluded_observations": len(unusable),
        "excluded_sources": len(set(unusable.source_id) - set(selected.source_id) - {""}),
        "unresolved_observations": int(manifest.class_label.eq("UNRESOLVED").sum()),
        "feature_representation": representation, "spectral_grid_status": "verified" if grid_hashes else "not_applicable_PM_only",
        "verified_grid_hashes": sorted(grid_hashes), "observations_with_errors": error_counts,
        "provenance_complete": True,
        "duplicate_status": "checked_no_duplicates" if grid_hashes else "identifiers_checked; spectra_unavailable_PM_only",
        "input_product_checksums": all_file_checksums,
    }
