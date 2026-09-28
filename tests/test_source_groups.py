import pytest

from bhns.data.source_manifest import build_source_manifest, validate_manifest
from bhns.data.validation import DatasetValidationError, validate_source_groups


@pytest.mark.parametrize("column,value", [("compact_object_class", "NS"),
    ("source_id", "other-id"), ("source_name", "UNREVIEWED ALIAS")])
def test_one_source_has_one_label_and_group(observations, column, value):
    observations.loc[0, column] = value
    with pytest.raises(DatasetValidationError, match="Conflicting"):
        validate_source_groups(observations)


def test_two_names_cannot_share_id(observations):
    observations.loc[observations.source_name.eq("TEST SOURCE 01"), "source_id"] = "test-id-00"
    with pytest.raises(DatasetValidationError):
        validate_source_groups(observations)


def test_manifest_uses_actual_counts_and_evidence(observations, provenance):
    manifest = build_source_manifest(observations, provenance)
    assert manifest.n_observations.sum() == len(observations)
    assert len(manifest) == 12  # The expected 61 never overrides actual counts.
    assert manifest.label_reference.notna().all()
    validate_manifest(observations, manifest)


def test_provenance_never_silently_relabels(observations, provenance):
    provenance.loc[provenance.index[0], "compact_object_class"] = "NS"
    with pytest.raises(DatasetValidationError, match="no automatic correction"):
        build_source_manifest(observations, provenance)
    assert observations.loc[0, "compact_object_class"] == "BH"


def test_incomplete_provenance_rejected(observations, provenance):
    with pytest.raises(DatasetValidationError, match="cover exactly"):
        build_source_manifest(observations, provenance.iloc[1:])


def test_pending_labels_retained_but_block_primary_benchmark(observations, provenance):
    provenance["label_status"] = "pending"
    manifest = build_source_manifest(observations, provenance)
    with pytest.raises(DatasetValidationError, match="Pending/disputed"):
        validate_manifest(observations, manifest)
    validate_manifest(observations, manifest, require_verified=False)


def test_manifest_count_mismatch_fails(observations, provenance):
    manifest = build_source_manifest(observations, provenance)
    manifest.loc[0, "n_observations"] += 1
    with pytest.raises(DatasetValidationError, match="counts"):
        validate_manifest(observations, manifest)
