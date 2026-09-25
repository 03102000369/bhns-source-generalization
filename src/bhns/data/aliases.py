"""Exact, evidence-backed identity resolution; never fuzzy-match an object."""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from bhns.data.validation import DatasetValidationError, require_text


class UnknownSourceError(DatasetValidationError):
    pass


class AmbiguousAliasError(DatasetValidationError):
    pass


def name_key(name):
    if not isinstance(name, str) or not name.strip():
        raise UnknownSourceError("Missing source name")
    # Formatting only. No punctuation removal, coordinate rounding or edit distance.
    return " ".join(name.split()).casefold()


def validate_registry(registry):
    required = ["source_id", "canonical_source_name", "class_label", "classification_status",
                "classification_reference", "classification_evidence", "identity_reference"]
    if not registry.columns.is_unique:
        raise DatasetValidationError("Duplicate registry columns")
    require_text(registry, required)
    if registry.source_id.duplicated().any() or registry.canonical_source_name.map(name_key).duplicated().any():
        raise DatasetValidationError("Duplicate canonical identity in source registry")
    if not registry.class_label.isin(["BH", "NS", "UNRESOLVED"]).all():
        raise DatasetValidationError("Invalid registry class label")
    if not registry.classification_status.isin(["verified", "unresolved", "disputed"]).all():
        raise DatasetValidationError("Invalid classification status")
    if ((registry.class_label == "UNRESOLVED") & (registry.classification_status == "verified")).any():
        raise DatasetValidationError("An unresolved label cannot be verified")
    return registry


@dataclass(frozen=True)
class SourceResolution:
    raw_name: str
    source_id: str
    canonical_source_name: str
    mapping_reference: str
    mapping_kind: str


class AliasResolver:
    def __init__(self, registry, aliases):
        validate_registry(registry)
        require_text(aliases, ["alias", "source_id", "alias_reference", "status"])
        if not aliases.status.isin(["verified", "unresolved", "disputed"]).all():
            raise DatasetValidationError("Invalid alias review status")
        self.registry = registry.copy()
        self._lookup = {}
        by_id = registry.set_index("source_id")
        for row in registry.itertuples(index=False):
            self._add(row.canonical_source_name, row.source_id, row.identity_reference, "canonical", "verified")
        for row in aliases.itertuples(index=False):
            if row.source_id not in by_id.index:
                raise DatasetValidationError("Alias points to an unknown canonical source")
            self._add(row.alias, row.source_id, row.alias_reference, "documented_alias", row.status)
        self._by_id = by_id

    def _add(self, name, source_id, reference, kind, status):
        key = name_key(name)
        self._lookup.setdefault(key, []).append((source_id, reference, kind, status))

    def canonicalize_source_name(self, raw_name):
        records = self._lookup.get(name_key(raw_name), [])
        if not records:
            raise UnknownSourceError(f"Unknown name; scientific review required: {raw_name}")
        if len({r[0] for r in records}) != 1:
            raise AmbiguousAliasError(f"Ambiguous alias: {raw_name}")
        # A competing unresolved/disputed mapping also vetoes automatic resolution.
        if any(r[3] != "verified" for r in records):
            raise UnknownSourceError(f"Unresolved alias evidence: {raw_name}")
        source_id, reference, kind, _ = records[0]
        return SourceResolution(raw_name, source_id, self._by_id.loc[source_id, "canonical_source_name"], reference, kind)


def canonicalize_source_name(raw_name, *, registry_path=None, aliases_path=None):
    """Resolve using the supplied registry or this project's reviewed local registry."""
    root = Path(__file__).resolve().parents[3]
    registry_path = registry_path or root / "data/manifests/source_registry.csv"
    aliases_path = aliases_path or root / "data/manifests/source_aliases.csv"
    resolver = AliasResolver(pd.read_csv(registry_path, keep_default_na=False),
                             pd.read_csv(aliases_path, keep_default_na=False))
    return resolver.canonicalize_source_name(raw_name)
