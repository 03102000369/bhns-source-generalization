"""Authoritative scientific data gate. Structural validity alone cannot pass."""

from pathlib import Path
import json
from zipfile import BadZipFile

import pandas as pd

from bhns.constants import ERROR_COLUMNS, FLUX_COLUMNS
from bhns.data.aliases import validate_registry
from bhns.data.cohort import as_bool, validate_cohort
from bhns.data.loaders import load_observations
from bhns.data.source_manifest import validate_manifest
from bhns.reproducibility import file_sha256, run_record, write_json

DEFAULT_INPUTS = {
    "observation_table": "data/processed/observations.csv",
    "observation_manifest": "data/manifests/observation_manifest.csv",
    "source_registry": "data/manifests/source_registry.csv",
    "source_aliases": "data/manifests/source_aliases.csv",
    "product_provenance": "data/provenance/observation_provenance.csv",
    "external_sources": "data/provenance/external_sources.csv",
    "energy_grids": "data/manifests/energy_grids.json",
    "pm_definitions": "data/manifests/pm_feature_definitions.json",
    "source_manifest": "data/manifests/source_manifest.csv",
}


def _csv(path):
    # Preserve IDs and textual true/false values until strict validation.
    import csv
    with Path(path).open(newline="") as handle:
        header = next(csv.reader(handle), [])
    if len(set(header)) != len(header):
        raise ValueError(f"Duplicate CSV header in {path}")
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def run_gate1(root, config):
    root = Path(root)
    paths = {key: root / config["data"].get(key, value) for key, value in DEFAULT_INPUTS.items()}
    record = run_record(config, project_root=root, experiment_name="gate1-scientific-data")
    record.update(status="BLOCKED", gate=1, validation_kind="scientific_data", scientific_ready=False,
                  record_kind="scientific_data_admission_audit",
                  problems=[], input_checksums={}, summary={
                      "observations": 0, "unique_sources": 0, "BH_sources": 0, "NS_sources": 0,
                      "BH_observations": 0, "NS_observations": 0,
                      "excluded_sources": None, "excluded_observations": None, "unresolved_sources": None,
                      "unresolved_observations": None,
                      "feature_availability": {"spectral": False, "errors": False, "PM": False, "combined": False},
                      "spectral_grid_status": "unavailable", "provenance_complete": False,
                      "duplicate_status": "not_assessable_no_canonical_observations",
                      "count_scope": "trusted_ingested_cohort; population and exclusions unknown until data acquisition",
                  }, registry_inventory=None, discovery_inventory={})
    try:
        if config["data"].get("n_spectral_bins", 43) != 43:
            raise ValueError("The current spectral intake schema supports exactly 43 bins; review/version a different representation explicitly")
        for name, relative in {
            "archive_query": "data/provenance/archive_query.json",
            "archive_probe": "data/provenance/archive_probe_audit.json",
        }.items():
            path = root / relative
            if path.is_file():
                evidence = json.loads(path.read_text())
                record["discovery_inventory"][name] = {
                    "path": relative, "sha256": file_sha256(path),
                    "note": "Discovery evidence only; not admitted to the canonical cohort",
                }
                if name == "archive_query":
                    record["discovery_inventory"][name].update({key: evidence.get(key) for key in
                        ("metadata_rows", "archived_rows", "rows_without_obsid")})
                else:
                    record["discovery_inventory"][name].update(standard_products=len(evidence.get("products", {})),
                        archive_directory_obsid=evidence.get("rxte_directory_obsid"), usable=False)
        if paths["source_registry"].is_file():
            registry = _csv(paths["source_registry"])
            validate_registry(registry)
            record["registry_inventory"] = {"reviewed_objects": len(registry),
                "BH": int(registry.class_label.eq("BH").sum()), "NS": int(registry.class_label.eq("NS").sum()),
                "UNRESOLVED": int(registry.class_label.eq("UNRESOLVED").sum()),
                "note": "Literature identity review only; not an observational cohort"}
        for key, path in paths.items():
            if path.is_file():
                record["input_checksums"][str(path.relative_to(root) if path.is_relative_to(root) else path)] = file_sha256(path)
            else:
                record["problems"].append(f"Missing {key}: {path}")
        if not record["problems"]:
            representation = config["data"].get("feature_representation", "SM")
            manifest = _csv(paths["observation_manifest"])
            if manifest.empty or not manifest.usable.map(as_bool).any():
                record["problems"].append("Observation manifest has zero usable entries; no verified observational cohort")
            else:
                frame = load_observations(paths["observation_table"], representation=representation)
                summary = validate_cohort(frame, manifest, registry, _csv(paths["source_aliases"]),
                    _csv(paths["product_provenance"]), _csv(paths["external_sources"]),
                    json.loads(paths["energy_grids"].read_text()).get("grids", {}),
                    json.loads(paths["pm_definitions"].read_text()).get("definitions", {}),
                    root=root, representation=representation)
                # Retain the original source census consistency check.
                census = _csv(paths["source_manifest"])
                census["n_observations"] = pd.to_numeric(census.n_observations, errors="raise")
                validate_manifest(frame, census)
                if summary["BH_sources"] == 0 or summary["NS_sources"] == 0:
                    record["problems"].append("Both verified BH and NS sources are required for the binary benchmark")
                else:
                    summary["feature_availability"] = {
                        "spectral": summary["spectral_grid_status"] == "verified" and set(FLUX_COLUMNS) <= set(frame),
                        "errors": summary["observations_with_errors"] == summary["observations"] and set(ERROR_COLUMNS) <= set(frame),
                        "PM": representation.upper() in {"PM", "COMBINED"},
                        "combined": representation.upper() == "COMBINED",
                    }
                    summary["unresolved_sources"] = int(manifest.loc[manifest.class_label.eq("UNRESOLVED"), "source_id"].replace("", pd.NA).nunique())
                    record.update(summary=summary, status="PASS", scientific_ready=True)
    except (ValueError, OSError, KeyError, TypeError, BadZipFile, EOFError, ImportError) as exc:
        record["status"] = "FAIL"
        record["problems"].append(str(exc))
    if record["status"] != "PASS":
        record["problems"].append("No scientific model training is permitted. Obtain measured products, exact ObsID/source mapping and verified record-level provenance.")
    write_json(root / "reports/gate1_data_report.json", record)
    lines = ["# Gate 1 scientific data report", "", f"Status: **{record['status']}**", "",
             f"UTC: {record['timestamp_utc']}", "",
             f"Configuration SHA-256: `{record['configuration_hash']}`", "",
             "## Trusted dataset status", "", "```json", json.dumps(record["summary"], indent=2), "```", "",
             "Zero means no trusted records ingested. Null means unknown/not assessable, not zero exclusions.", "",
             "## Separate literature registry", "", "```json", json.dumps(record["registry_inventory"], indent=2), "```", "",
             "Registry objects and the published source-results roster are not admitted observations.", "",
             "## Separate archive discoveries", "", "```json", json.dumps(record["discovery_inventory"], indent=2), "```", "",
             "## Acceptance checks", "",
             "The scientific gate checks exact identities, documented aliases, class evidence, original-product and processing-log checksums,",
             "valid and unique RXTE ObsIDs, explicit usable flags, feature/product equality, per-spectrum grids/errors, PM definitions and duplicates.",
             "A legacy structural-audit PASS is insufficient. No absent measurement or uncertainty is imputed at intake.", "",
             "## Blockers or failures", ""]
    lines += [f"- {p}" for p in record["problems"]] or ["- None in the configured cohort."]
    lines += ["", "## Evidence and next action", "",
              "See [acquisition investigation](data_acquisition_report.md), [identity review](source_identity_review_XTE_J1908_4U1907.md),",
              "[grid audit](energy_grid_audit.md), [PM definitions](pm_feature_definition_audit.md),",
              "[source-registry audit](source_registry_audit.md), and [external-source register](../data/provenance/external_sources.csv).", "",
              "Request the authors' processed arrays plus exact ObsID/source mapping and reduction/fit settings, or reconstruct a new",
              "independently documented PCA cohort with HEASoft/CALDB. Review native grids before choosing a representation.", "",
              "Do not freeze a scientific protocol or enable Gate 3 while this gate is not PASS.", ""]
    (root / "reports/gate1_data_report.md").write_text("\n".join(lines))
    return record
