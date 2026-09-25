from pathlib import Path

import numpy as np
import pytest
import yaml

from bhns.cli import audit_dataset, main
from bhns.config import load_config
from bhns.data.provenance import validate_dataset_provenance
from bhns.data.source_manifest import build_source_manifest
from bhns.data.validation import DatasetValidationError
from bhns.gates import deferred
from bhns.reproducibility import file_sha256

ROOT = Path(__file__).resolve().parents[1]


def test_absent_data_gate_blocks_without_creating_fake_data(tmp_path):
    config = load_config(ROOT / "configs/base.yaml")
    record = audit_dataset(tmp_path, config)
    assert record["status"] == "BLOCKED"
    assert record["summary"] is None
    assert record["metrics"] is None
    assert not (tmp_path / "data/processed/observations.csv").exists()


def test_later_gate_cannot_execute():
    with pytest.raises(SystemExit, match="Gates 0–2"):
        deferred("LOSO training")


def test_valid_schema_without_acquisition_provenance_cannot_pass(observations, provenance, tmp_path):
    config = load_config(ROOT / "configs/base.yaml")
    observations.to_csv(tmp_path / "observations.csv", index=False)
    build_source_manifest(observations, provenance).to_csv(tmp_path / "manifest.csv", index=False)
    result = audit_dataset(tmp_path, config, observations="observations.csv", manifest="manifest.csv")
    assert result["status"] == "BLOCKED"


def test_data_provenance_is_bound_to_file_checksum(observations, tmp_path):
    config = load_config(ROOT / "configs/base.yaml")
    table = tmp_path / "observations.csv"
    observations.to_csv(table, index=False)
    record = {key: "TEST ONLY" for key in ["origin_reference", "reduction_reference", "flux_units",
              "error_definition", "source_mapping_review", "reviewed_by", "reviewed_at"]}
    record.update(status="verified", instrument="RXTE/PCA", canonical_sha256=file_sha256(table),
                  spectral_bin_edges_keV=np.linspace(5, 25, 44).tolist())
    path = tmp_path / "provenance.yaml"
    path.write_text(yaml.safe_dump(record))
    validate_dataset_provenance(path, table, config)
    with table.open("a") as f:
        f.write("\n")
    with pytest.raises(DatasetValidationError, match="checksum"):
        validate_dataset_provenance(path, table, config)


def test_unverified_labels_fail_gate(observations, provenance, tmp_path):
    config = load_config(ROOT / "configs/base.yaml")
    observations.to_csv(tmp_path / "observations.csv", index=False)
    provenance["label_status"] = "pending"
    build_source_manifest(observations, provenance).to_csv(tmp_path / "manifest.csv", index=False)
    result = audit_dataset(tmp_path, config, observations="observations.csv", manifest="manifest.csv")
    assert result["status"] == "FAIL"
    assert "Pending/disputed" in result["problems"][0]


def test_complete_review_can_pass_without_forcing_reference_counts(observations, provenance, tmp_path):
    # Artificial fixture tests the successful software path only, in pytest's temp directory.
    config = load_config(ROOT / "configs/base.yaml")
    table = tmp_path / "observations.csv"
    observations.to_csv(table, index=False)
    build_source_manifest(observations, provenance).to_csv(tmp_path / "manifest.csv", index=False)
    record = {key: "TEST ONLY" for key in ["origin_reference", "reduction_reference", "flux_units",
              "error_definition", "source_mapping_review", "reviewed_by", "reviewed_at"]}
    record.update(status="verified", instrument="RXTE/PCA", canonical_sha256=file_sha256(table),
                  spectral_bin_edges_keV=np.linspace(5, 25, 44).tolist())
    path = tmp_path / config["data"]["dataset_provenance"]
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(record))
    result = audit_dataset(tmp_path, config, observations="observations.csv", manifest="manifest.csv")
    assert result["status"] == "PASS"
    assert result["summary"]["sources"] == 12
    assert result["count_differences"]["sources"] == -49
    assert result["metrics"] is None
