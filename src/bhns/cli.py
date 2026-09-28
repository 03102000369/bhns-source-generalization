"""Gate 0–2 commands. No training commands are implemented or dispatched."""

import argparse
import json
import logging
from pathlib import Path
import sys

from bhns.config import load_config
from bhns.data.loaders import DataGateBlocked, load_observations, read_table
from bhns.data.provenance import validate_dataset_provenance
from bhns.data.source_manifest import build_source_manifest, empty_manifest, save_manifest
from bhns.data.validation import dataset_summary
from bhns.gates import deferred
from bhns.reproducibility import configure_logging, environment_record, run_record, write_json

LOG = logging.getLogger(__name__)


def _path(root, value):
    path = Path(value)
    return path if path.is_absolute() else root / path


def audit_dataset(root, config, *, observations=None, manifest=None):
    """Legacy structural intake audit; PASS here is NOT scientific Gate 1 PASS.

    Kept for compatibility with the initial foundation's callers and tests.
    New scientific acceptance is bhns.data.gate1.run_gate1.
    """
    root = Path(root).resolve()
    observations = _path(root, observations or config["data"]["observation_table"])
    manifest = _path(root, manifest or config["data"]["source_manifest"])
    record = run_record(config, project_root=root, experiment_name="data-audit")
    record.update({"gate": "structural_intake_only", "status": "BLOCKED", "scientific_ready": False, "observation_path": str(observations),
                   "manifest_path": str(manifest), "summary": None, "problems": [],
                   "expected_counts": config["data"]["expected_counts"], "count_differences": None})
    if not observations.is_file():
        record["problems"].append("No canonical RXTE/PCA observation table is available. Zero records ingested; the astronomical population is unknown.")
    else:
        try:
            frame = load_observations(observations,
                                      allow_missing_features=config["data"]["allow_missing_features"],
                                      representation=config["data"].get("feature_representation"))
            record["summary"] = dataset_summary(frame)
            # A valid shape alone does not establish label or dataset provenance.
            from bhns.data.source_manifest import validate_manifest
            validate_manifest(frame, read_table(manifest))
            validate_dataset_provenance(_path(root, config["data"]["dataset_provenance"]), observations, config)
            record["status"] = "PASS"
            record["count_differences"] = {
                key: record["summary"][key] - value for key, value in record["expected_counts"].items()
            }
        except DataGateBlocked as exc:
            record["problems"].append(str(exc))
        except (ValueError, OSError, ImportError) as exc:
            record["status"] = "FAIL"
            record["problems"].append(str(exc))
    write_json(root / "reports/data_audit.json", record)
    _write_audit_markdown(root, record)
    return record


def _write_audit_markdown(root, record):
    summary = record["summary"]
    lines = ["# Structural data audit", "", f"Structural intake: **{record['status']}**", "",
             "This legacy check cannot confer scientific Gate 1 PASS. See [the authoritative Gate 1 report](gate1_data_report.md).", "",
             f"Audit UTC: {record['timestamp_utc']}", "",
             f"Configuration hash: `{record['configuration_hash']}`", "",
             "## Data inventory", "",
             f"Canonical file: `{record['observation_path']}`", "",
             f"Source manifest: `{record['manifest_path']}`", ""]
    if summary is None:
        lines += [
            "No eligible canonical observations ingested: sources=0, BH=0, NS=0, observations=0.",
            "These are inventory counts, not measurements of the intended sample.", "",
            "| Audit item | Finding |", "|---|---|",
            "| Observations per source | Not assessable |",
            "| Spectral dimensions | Required: 43; observed: unavailable |",
            "| Error arrays | Unavailable for this benchmark |",
            "| Five PM parameters | Unavailable for this benchmark |",
            "| Missing feature values | Not assessable without observations |",
            "| Duplicate observations | Not assessable without observations |",
            "| Conflicting/missing labels | Not assessable without observations |", "",
        ]
    else:
        lines += ["```json", json.dumps(summary, indent=2), "```", ""]
    lines += ["## Provenance and availability", "",
              "See [local inventory](../data/manifests/local_inventory.json) for the bounded local inspection, including incompatible monitoring products.", "",
              "No processed download matching the reference 43-bin cohort was verified. Three real standard archive products were separately acquired as an unusable probe; see [acquisition findings](data_acquisition_report.md).", "",
              "[Pattnaik et al.](https://arxiv.org/html/2012.06934v1) points to HEASARC for data availability. The [RXTE archive](https://heasarc.gsfc.nasa.gov/docs/xte/archive.html) is a verified acquisition route, but raw/standard products require reviewed selection and reduction before becoming this canonical dataset.", "",
              "## Reference census comparison", "",
              f"Expected counts (comparison only): `{record['expected_counts']}`.", "",
              f"Actual minus expected: `{record['count_differences']}` (null means no completed provenance-validated comparison).", "",
              "## Label review", "",
              "The manifest records only ingested sources. It is header-only when data are absent; no labels are inferred from expected counts.",
              "Retain the reference's XTE J1908+094 / 4U 1907+097 issue for ObsID-level review. No automatic relabeling or alias substitution is implemented.", "",
              "## Problems", ""]
    lines += [f"- {p}" for p in record["problems"]] or ["- No validation errors found in the supplied files."]
    lines += ["", "## Acquisition and next gate", "",
              "Follow [the acquisition checklist](../data/acquisition_checklist.md) and [canonical schema](../data/README.md).",
              "No model has been trained. Stop for scientific review of Gates 0–2 before Gate 3.", ""]
    (root / "reports/data_audit.md").write_text("\n".join(lines))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["environment", "manifest", "validate", "summary", "deferred"])
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--config", default="configs/base.yaml")
    parser.add_argument("--observations")
    parser.add_argument("--manifest")
    parser.add_argument("--provenance")
    parser.add_argument("--stage", default="scientific experiments")
    args = parser.parse_args(argv)
    configure_logging()
    root = args.project_root.resolve()
    if args.command == "deferred":
        deferred(args.stage)
    if args.command == "environment":
        environment = environment_record()
        environment["status"] = "PASS" if sys.version_info >= (3, 11) and all(environment["packages"].values()) else "FAIL"
        write_json(root / "reports/environment.json", environment)
        print(json.dumps(environment, indent=2))
        return 0 if environment["status"] == "PASS" else 1
    config = load_config(_path(root, args.config))
    if args.command == "manifest":
        output = _path(root, args.manifest or config["data"]["source_manifest"])
        try:
            frame = load_observations(_path(root, args.observations or config["data"]["observation_table"]),
                                      allow_missing_features=config["data"]["allow_missing_features"],
                                      representation=config["data"].get("feature_representation"))
            labels = read_table(_path(root, args.provenance or config["data"]["label_provenance"]))
            manifest = build_source_manifest(frame, labels)
            save_manifest(manifest, output)
            LOG.info("Wrote %d observed sources to %s; run validate to review provenance", len(manifest), output)
            return 0
        except DataGateBlocked as exc:
            if not output.exists():
                save_manifest(empty_manifest(), output)
            LOG.warning("Gate 1 BLOCKED: %s. No source rows invented.", exc)
            return 2
        except (ValueError, OSError) as exc:
            LOG.error("Manifest validation failed: %s", exc)
            return 1
    from bhns.data.gate1 import run_gate1
    if args.observations:
        config["data"]["observation_table"] = args.observations
    if args.manifest:
        config["data"]["source_manifest"] = args.manifest
    audit_dataset(root, config)
    record = run_gate1(root, config)
    print(json.dumps({k: record[k] for k in ("status", "summary", "problems")}, indent=2))
    return {"PASS": 0, "BLOCKED": 2, "FAIL": 1}[record["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
