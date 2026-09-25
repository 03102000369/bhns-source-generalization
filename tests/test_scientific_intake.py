"""SYNTHETIC software fixtures ONLY; no astronomical records or measurements.

All artifact bytes and ObsID-shaped strings remain in pytest temporary storage.
"""

from copy import deepcopy
import json

import numpy as np
import pandas as pd
import pytest

from bhns.constants import ERROR_COLUMNS, FLUX_COLUMNS, PARAMETER_COLUMNS
from bhns.data.aliases import AliasResolver, AmbiguousAliasError, UnknownSourceError, validate_registry, canonicalize_source_name
from bhns.data.cohort import (OBSERVATION_MANIFEST_COLUMNS, PRODUCT_PROVENANCE_COLUMNS,
                              as_bool, valid_rxte_obsid, validate_cohort)
from bhns.data.gate1 import DEFAULT_INPUTS, run_gate1
from bhns.data.source_manifest import build_source_manifest
from bhns.data.spectral_products import inspect_energy_grid, inspect_product, validate_uncertainties
from bhns.data.validation import DatasetValidationError
from bhns.reproducibility import file_sha256


@pytest.fixture
def synthetic_cohort(tmp_path):
    """Create explicitly synthetic local product/provenance contracts, never data/."""
    def factory(representation="SM", with_errors=True):
        registry = pd.DataFrame([
            dict(source_id=f"SYNTHETIC-{i}", canonical_source_name=f"SYNTHETIC SOURCE {i}",
                 class_label=label, classification_status="verified", classification_reference="TEST-EVIDENCE",
                 classification_evidence="SYNTHETIC TEST ONLY", identity_reference="TEST-EVIDENCE")
            for i, label in enumerate(["BH", "NS"])
        ])
        aliases = pd.DataFrame([dict(alias="SYNTHETIC ALIAS", source_id="SYNTHETIC-0",
                                    alias_reference="TEST-EVIDENCE", status="verified")])
        external = pd.DataFrame([dict(reference_id="TEST-EVIDENCE", access_status="verified",
            **{f"supports_{kind}": "true" for kind in
               ["classification", "alias", "observation_mapping", "spectrum", "pm_features"]})])
        edges = np.linspace(5, 25, 44)
        grid = inspect_energy_grid(edges[:-1], edges[1:])
        grids = {"TEST-GRID": dict(status="verified", grid_sha256=grid["grid_sha256"],
            nominal_band_keV=[5, 25], native_bounds_reviewed=True,
            review_notes="SYNTHETIC grid only", review_reference="TEST-EVIDENCE")}
        definitions = {"TEST-PM": dict(status="verified", parameters={c: dict(
            definition="SYNTHETIC definition", units="SYNTHETIC units", fit_method="SYNTHETIC method",
            reference="TEST-EVIDENCE") for c in PARAMETER_COLUMNS})}
        observations, manifests, products = [], [], []
        for number in range(4):
            source = registry.iloc[number % 2]
            identifier = f"SYNTHETIC-OBS-{number}"
            # Syntax fixture, NOT a claimed or downloaded RXTE observation.
            rxte = f"99999-99-{number:02d}-00"
            raw, product, log = (tmp_path / f"SYNTHETIC-{number}.{ext}" for ext in ["raw", "npz", "json"])
            raw.write_text(f"SYNTHETIC raw bytes {number}; no observational data")
            log.write_text(json.dumps({"synthetic": True, "test_row": number}))
            payload = {}
            row = dict(obs_id=identifier, source_id=source.source_id,
                       source_name=source.canonical_source_name, compact_object_class=source.class_label)
            if representation != "PM":
                payload.update(flux=np.arange(43, dtype=float) + number / 10,
                               energy_lo_keV=edges[:-1], energy_hi_keV=edges[1:])
                row.update(zip(FLUX_COLUMNS, payload["flux"]))
                if with_errors:
                    payload["errors"] = np.full(43, 0.1)
                    row.update(zip(ERROR_COLUMNS, payload["errors"]))
            if representation in {"PM", "COMBINED"}:
                payload.update({c: float(number + i + 1) for i, c in enumerate(PARAMETER_COLUMNS)})
                row.update({c: payload[c] for c in PARAMETER_COLUMNS})
            np.savez(product, **payload)
            manifest = dict.fromkeys(OBSERVATION_MANIFEST_COLUMNS, "")
            manifest.update(observation_id=identifier, rxte_obsid=rxte, source_id=source.source_id,
                canonical_source=source.canonical_source_name, raw_source_name=source.canonical_source_name,
                class_label=source.class_label, instrument="RXTE/PCA", data_product="SYNTHETIC TEST NPZ",
                spectrum_path_or_reference=product.name if "flux" in payload else "",
                error_path_or_reference=product.name if "errors" in payload else "",
                energy_grid_id="TEST-GRID" if "flux" in payload else "",
                feature_record_id=identifier, provenance_record_id=f"TEST-PROV-{number}", usable="true")
            provenance = dict.fromkeys(PRODUCT_PROVENANCE_COLUMNS, "")
            provenance.update(provenance_record_id=manifest["provenance_record_id"], observation_id=identifier,
                rxte_obsid=rxte, source_id=source.source_id, status="verified", original_location="SYNTHETIC TEST ONLY",
                raw_path=raw.name, raw_sha256=file_sha256(raw), product_path=product.name,
                product_sha256=file_sha256(product), processing_log_path=log.name, processing_log_sha256=file_sha256(log),
                acquisition_date="2000-01-01T00:00:00Z", preprocessing_method="SYNTHETIC TEST ONLY",
                feature_extraction_version="TEST-1", source_mapping_reference="TEST-EVIDENCE", source_mapping_status="verified",
                flux_units="SYNTHETIC", error_units="SYNTHETIC", error_definition="SYNTHETIC standard error",
                zero_error_policy="reject", energy_grid_id=manifest["energy_grid_id"], pm_definition_id="TEST-PM")
            observations.append(row); manifests.append(manifest); products.append(provenance)
        return dict(frame=pd.DataFrame(observations), manifest=pd.DataFrame(manifests), registry=registry,
                    aliases=aliases, products=pd.DataFrame(products), external_sources=external,
                    grids=grids, pm_definitions=definitions, root=tmp_path, representation=representation)
    return factory


def test_documented_alias_preserves_raw_name(synthetic_cohort):
    d = synthetic_cohort()
    result = AliasResolver(d["registry"], d["aliases"]).canonicalize_source_name(" synthetic   alias ")
    assert result.source_id == "SYNTHETIC-0"
    assert result.raw_name == " synthetic   alias "
    assert result.mapping_reference == "TEST-EVIDENCE"


@pytest.mark.parametrize("name", ["SYNTHETIC SOURC 0", "SYNTHETICSOURCE0", "", "UNKNOWN"])
def test_unknown_and_near_match_fail(synthetic_cohort, name):
    d = synthetic_cohort()
    with pytest.raises(UnknownSourceError):
        AliasResolver(d["registry"], d["aliases"]).canonicalize_source_name(name)


def test_ambiguous_alias_fail(synthetic_cohort):
    d = synthetic_cohort()
    d["aliases"] = pd.concat([d["aliases"], d["aliases"].assign(source_id="SYNTHETIC-1")])
    with pytest.raises(AmbiguousAliasError):
        AliasResolver(d["registry"], d["aliases"]).canonicalize_source_name("SYNTHETIC ALIAS")


def test_duplicate_canonical_identity_fails(synthetic_cohort):
    d = synthetic_cohort()
    d["registry"].loc[1, "canonical_source_name"] = "synthetic source 0"
    with pytest.raises(DatasetValidationError, match="Duplicate canonical"):
        validate_registry(d["registry"])


def test_reviewed_xte_and_4u_names_never_merge():
    # Real literature names only; no observation or measurement fixture is made.
    xte = canonicalize_source_name("XTE J1908+094")
    pulsar = canonicalize_source_name("4U 1907+097")
    assert xte.source_id != pulsar.source_id
    assert canonicalize_source_name("SAX J1819.3-2525").source_id == canonicalize_source_name("V4641 Sgr").source_id


@pytest.mark.parametrize("family,errors", [("SM", False), ("SM", True), ("SEM", True), ("PM", False), ("COMBINED", False)])
def test_verified_synthetic_contract_all_feature_families(synthetic_cohort, family, errors):
    summary = validate_cohort(**synthetic_cohort(family, errors))
    assert summary["observations"] == 4 and summary["unique_sources"] == 2
    assert summary["BH_sources"] == summary["NS_sources"] == 1


@pytest.mark.parametrize("table,column,value,match", [
    ("manifest", "rxte_obsid", "not-an-obsid", "Malformed RXTE"),
    ("manifest", "class_label", "UNRESOLVED", "Unresolved"),
    ("manifest", "class_label", "NS", "Class label"),
    ("manifest", "raw_source_name", "UNKNOWN", "Unknown name"),
    ("manifest", "source_id", "SYNTHETIC-1", "Alias and canonical"),
    ("manifest", "usable", "false", "exclusion_reason"),
    ("products", "status", "unresolved", "Unresolved observation"),
    ("products", "raw_sha256", "0" * 64, "Checksum mismatch"),
    ("products", "product_sha256", "0" * 64, "Checksum mismatch"),
    ("products", "processing_log_sha256", "0" * 64, "Checksum mismatch"),
    ("products", "original_location", "", "Missing provenance"),
    ("products", "source_mapping_reference", "UNKNOWN", "Missing external evidence"),
    ("products", "acquisition_date", "NaT", "Invalid acquisition"),
    ("products", "source_id", "SYNTHETIC-1", "different observation/source"),
    ("external_sources", "supports_classification", "false", "does not support"),
])
def test_scientific_admission_fails_closed(synthetic_cohort, table, column, value, match):
    d = synthetic_cohort()
    d[table].loc[0, column] = value
    with pytest.raises(DatasetValidationError, match=match):
        validate_cohort(**d)


@pytest.mark.parametrize("key", ["observation_id", "rxte_obsid", "feature_record_id", "provenance_record_id"])
def test_duplicate_observation_identifiers_fail(synthetic_cohort, key):
    d = synthetic_cohort()
    d["manifest"].loc[1, key] = d["manifest"].loc[0, key]
    with pytest.raises(DatasetValidationError, match="Duplicate|Repeated"):
        validate_cohort(**d)


def test_false_is_not_truthy_and_excluded_rows_not_admitted(synthetic_cohort):
    d = synthetic_cohort()
    d["manifest"].loc[0, ["usable", "exclusion_reason"]] = ["false", "SYNTHETIC exclusion"]
    with pytest.raises(DatasetValidationError, match="usable observation set"):
        validate_cohort(**d)
    d["frame"] = d["frame"].iloc[1:].copy()
    assert validate_cohort(**d)["excluded_observations"] == 1
    assert as_bool("false") is False
    with pytest.raises(DatasetValidationError):
        as_bool(1)


def _rewrite_product(d, index, **changes):
    path = d["root"] / d["products"].loc[index, "product_path"]
    with np.load(path, allow_pickle=False) as original:
        arrays = {name: original[name] for name in original.files}
    arrays.update(changes)
    np.savez(path, **arrays)
    d["products"].loc[index, "product_sha256"] = file_sha256(path)


def test_duplicate_spectra_detected_across_different_obsids(synthetic_cohort):
    d = synthetic_cohort()
    values = d["frame"].loc[0, list(FLUX_COLUMNS)].to_numpy(float)
    d["frame"].loc[1, list(FLUX_COLUMNS)] = values
    _rewrite_product(d, 1, flux=values)
    with pytest.raises(DatasetValidationError, match="Duplicate spectra"):
        validate_cohort(**d)


def test_canonical_measurements_must_equal_product(synthetic_cohort):
    d = synthetic_cohort()
    d["frame"].loc[0, "flux_00"] += 1
    with pytest.raises(DatasetValidationError, match="flux values disagree"):
        validate_cohort(**d)


def test_mixed_grids_rejected_even_when_individually_reviewed(synthetic_cohort):
    d = synthetic_cohort()
    edges = np.linspace(5.01, 25.01, 44)
    grid = inspect_energy_grid(edges[:-1], edges[1:])
    d["grids"]["OTHER"] = deepcopy(d["grids"]["TEST-GRID"])
    d["grids"]["OTHER"]["grid_sha256"] = grid["grid_sha256"]
    d["manifest"].loc[1, "energy_grid_id"] = "OTHER"
    d["products"].loc[1, "energy_grid_id"] = "OTHER"
    _rewrite_product(d, 1, energy_lo_keV=edges[:-1], energy_hi_keV=edges[1:])
    with pytest.raises(DatasetValidationError, match="Non-identical native grids"):
        validate_cohort(**d)


def test_missing_grid_review_cannot_pass_by_hash_alone(synthetic_cohort):
    d = synthetic_cohort()
    d["grids"]["TEST-GRID"].pop("review_reference")
    with pytest.raises(DatasetValidationError, match="Missing external"):
        validate_cohort(**d)


@pytest.mark.parametrize("mutation", ["no_definition", "no_units", "bad_value"])
def test_pm_requires_verified_definitions_and_product_values(synthetic_cohort, mutation):
    d = synthetic_cohort("PM", False)
    if mutation == "no_definition":
        d["pm_definitions"] = {}
    elif mutation == "no_units":
        d["pm_definitions"]["TEST-PM"]["parameters"]["Gamma"]["units"] = ""
    else:
        d["frame"].loc[0, "Gamma"] += 1
    with pytest.raises(DatasetValidationError, match="PM"):
        validate_cohort(**d)


@pytest.mark.parametrize("lo,hi", [([1, 2], [2, 2]), ([2, 1], [3, 2]), ([1, 1.5], [2, 3]),
                                   ([1, np.nan], [2, 3]), ([-1, 1], [1, 2]), ([1, 2], [2])])
def test_invalid_energy_grids(lo, hi):
    with pytest.raises(DatasetValidationError):
        inspect_energy_grid(lo, hi)


@pytest.mark.parametrize("error,units,policy", [([0.1], "u", "reject"), ([0.1, -1], "u", "reject"),
    ([0.1, np.nan], "u", "reject"), ([0.1, 0], "u", "reject"), ([0.1, 1], "other", "reject")])
def test_invalid_uncertainties(error, units, policy):
    with pytest.raises(DatasetValidationError):
        validate_uncertainties([1, 2], error, flux_units="u", error_units=units, definition="test", zero_policy=policy)


def test_zero_errors_need_reason_in_provenance(synthetic_cohort):
    d = synthetic_cohort()
    d["products"].loc[0, "zero_error_policy"] = "documented_allow"
    with pytest.raises(DatasetValidationError, match="scientific justification"):
        validate_cohort(**d)


def test_orphan_error_product_rejected(tmp_path):
    path = tmp_path / "synthetic.npz"
    np.savez(path, errors=np.ones(43))
    with pytest.raises(DatasetValidationError, match="Orphan"):
        inspect_product(path, require_spectrum=False)


@pytest.mark.parametrize("value,expected", [("99999-99-00-00", True), ("99999-99-00-00A", True),
    ("99999-99-00-0A", False), ("null", False), (" 99999-99-00-00", False)])
def test_rxte_identifier_syntax_only(value, expected):
    assert valid_rxte_obsid(value) is expected


def _write_gate_inputs(d):
    root = d["root"]
    for path in DEFAULT_INPUTS.values():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
    for key, table in [("observation_table", "frame"), ("observation_manifest", "manifest"),
                       ("source_registry", "registry"), ("source_aliases", "aliases"),
                       ("product_provenance", "products"), ("external_sources", "external_sources")]:
        d[table].to_csv(root / DEFAULT_INPUTS[key], index=False)
    (root / DEFAULT_INPUTS["energy_grids"]).write_text(json.dumps({"grids": d["grids"]}))
    (root / DEFAULT_INPUTS["pm_definitions"]).write_text(json.dumps({"definitions": d["pm_definitions"]}))
    labels = d["frame"][["source_id", "source_name", "compact_object_class"]].drop_duplicates().assign(
        label_reference="TEST-EVIDENCE", label_status="verified", notes="SYNTHETIC ONLY")
    build_source_manifest(d["frame"], labels).to_csv(root / DEFAULT_INPUTS["source_manifest"], index=False)
    return {"seed": 42, "data": {"feature_representation": d["representation"]}, "experiment": {"name": "SYNTHETIC TEST"}}


def test_scientific_gate_pass_only_with_bound_products(synthetic_cohort):
    d = synthetic_cohort()
    config = _write_gate_inputs(d)
    assert run_gate1(d["root"], config)["status"] == "PASS"
    (d["root"] / d["products"].loc[0, "raw_path"]).write_text("SYNTHETIC tampered bytes")
    record = run_gate1(d["root"], config)
    assert record["status"] == "FAIL" and not record["scientific_ready"]


def test_table_and_legacy_pass_cannot_bypass_missing_provenance(synthetic_cohort):
    d = synthetic_cohort()
    config = _write_gate_inputs(d)
    (d["root"] / DEFAULT_INPUTS["product_provenance"]).unlink()
    (d["root"] / "reports").mkdir(exist_ok=True)
    (d["root"] / "reports/data_audit.json").write_text('{"status": "PASS"}')
    record = run_gate1(d["root"], config)
    assert record["status"] == "BLOCKED" and not record["scientific_ready"]


def test_header_only_canonical_placeholders_remain_blocked(synthetic_cohort):
    d = synthetic_cohort()
    config = _write_gate_inputs(d)
    d["frame"].iloc[:0].to_csv(d["root"] / DEFAULT_INPUTS["observation_table"], index=False)
    d["manifest"].iloc[:0].to_csv(d["root"] / DEFAULT_INPUTS["observation_manifest"], index=False)
    assert run_gate1(d["root"], config)["status"] == "BLOCKED"
