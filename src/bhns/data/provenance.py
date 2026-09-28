"""Gate 1 requires reviewed acquisition/reduction evidence, not just valid shapes."""

from pathlib import Path

import numpy as np
import yaml

from bhns.data.loaders import DataGateBlocked
from bhns.data.validation import DatasetValidationError
from bhns.reproducibility import file_sha256


def validate_dataset_provenance(path, observations_path, config):
    path = Path(path)
    if not path.is_file():
        raise DataGateBlocked(f"Dataset provenance is absent: {path}")
    record = yaml.safe_load(path.read_text())
    if not isinstance(record, dict) or record.get("status") != "verified":
        raise DataGateBlocked("Dataset acquisition/reduction provenance has not been verified")
    for key in ("origin_reference", "reduction_reference", "flux_units", "error_definition",
                "source_mapping_review", "reviewed_by", "reviewed_at"):
        if not isinstance(record.get(key), str) or not record[key].strip():
            raise DatasetValidationError(f"Missing dataset provenance field: {key}")
    if record.get("instrument") != "RXTE/PCA":
        raise DatasetValidationError("The primary benchmark requires RXTE/PCA spectra")
    if record.get("canonical_sha256") != file_sha256(observations_path):
        raise DatasetValidationError("Canonical observation file checksum disagrees with provenance")
    try:
        edges = np.asarray(record.get("spectral_bin_edges_keV"), dtype=float)
    except (TypeError, ValueError) as exc:
        raise DatasetValidationError("Invalid spectral bin edges") from exc
    if (edges.shape != (44,) or not np.isfinite(edges).all() or not (np.diff(edges) > 0).all()
            or not np.isclose(edges[0], config["data"]["energy_min_keV"])
            or not np.isclose(edges[-1], config["data"]["energy_max_keV"])):
        raise DatasetValidationError("Supply 44 increasing verified bin edges covering 5–25 keV")
    return record
