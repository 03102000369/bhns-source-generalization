"""Canonical table and representation definitions."""

from bhns.constants import ERROR_COLUMNS, FLUX_COLUMNS, IDENTITY_COLUMNS, PARAMETER_COLUMNS

REQUIRED_COLUMNS = IDENTITY_COLUMNS + FLUX_COLUMNS + ERROR_COLUMNS
OPTIONAL_METADATA = (
    "exposure", "mean_count_rate", "observation_date", "spectral_state",
    "instrument", "quality_flag",
)


def feature_columns(representation):
    """SEM uses [43 fluxes, 43 errors]; never include IDs or labels as features."""
    columns = {"SM": FLUX_COLUMNS, "RF": FLUX_COLUMNS,
               "SEM": FLUX_COLUMNS + ERROR_COLUMNS, "PM": PARAMETER_COLUMNS,
               "COMBINED": FLUX_COLUMNS + PARAMETER_COLUMNS}
    try:
        return columns[representation.upper()]
    except KeyError as exc:
        raise ValueError(f"Unknown representation: {representation}") from exc
