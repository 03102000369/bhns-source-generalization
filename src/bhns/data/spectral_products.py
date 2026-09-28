"""Inspect actual numerical products; no imputation, rebinning or error invention."""

import hashlib

import numpy as np

from bhns.constants import PARAMETER_COLUMNS
from bhns.data.validation import DatasetValidationError


def inspect_energy_grid(lower_keV, upper_keV, *, expected_bins=None):
    lower, upper = np.asarray(lower_keV, dtype=float), np.asarray(upper_keV, dtype=float)
    if lower.ndim != 1 or upper.shape != lower.shape or len(lower) == 0:
        raise DatasetValidationError("Energy boundaries must be equal nonempty 1-D arrays")
    if expected_bins is not None and len(lower) != expected_bins:
        raise DatasetValidationError(f"Expected {expected_bins} bins; found {len(lower)}")
    if not np.isfinite(lower).all() or not np.isfinite(upper).all():
        raise DatasetValidationError("Non-finite energy boundaries")
    if (lower < 0).any() or (upper <= lower).any():
        raise DatasetValidationError("Invalid energy-bin widths or negative energies")
    if (np.diff(lower) <= 0).any() or (np.diff(upper) <= 0).any() or (lower[1:] < upper[:-1]).any():
        raise DatasetValidationError("Unordered or overlapping energy bins")
    digest = hashlib.sha256(np.column_stack([lower, upper]).astype("<f8").tobytes()).hexdigest()
    return {"grid_sha256": digest, "n_bins": len(lower), "energy_min_keV": float(lower[0]),
            "energy_max_keV": float(upper[-1]), "gap_count": int((lower[1:] > upper[:-1]).sum()),
            "lower_keV": lower.tolist(), "upper_keV": upper.tolist()}


def validate_uncertainties(flux, errors, *, flux_units, error_units, definition, zero_policy="reject"):
    values, errors = np.asarray(flux, dtype=float), np.asarray(errors, dtype=float)
    if values.ndim != 1 or errors.shape != values.shape:
        raise DatasetValidationError("Uncertainty shape differs from spectral vector")
    if not np.isfinite(values).all() or not np.isfinite(errors).all() or (errors < 0).any():
        raise DatasetValidationError("Invalid spectral/uncertainty values")
    if not flux_units or error_units != flux_units or not definition:
        raise DatasetValidationError("Uncertainty units/definition are missing or incompatible")
    if zero_policy not in {"reject", "documented_allow"}:
        raise DatasetValidationError("Unknown zero-error policy")
    if (errors == 0).any() and zero_policy == "reject":
        raise DatasetValidationError("Zero errors require an explicit reviewed policy")
    return {"available": True, "zero_count": int((errors == 0).sum()), "definition": definition}


def inspect_product(path, *, expected_bins=43, require_spectrum=True, require_errors=False,
                    require_pm=False, flux_units="", error_units="", error_definition="", zero_policy="reject"):
    """Named NPZ interchange: flux, energy_lo_keV, energy_hi_keV; optional errors/PM.

    This is a validation format, not a raw FITS reduction. The conversion must be
    separately documented and checksummed. allow_pickle=False forbids object payloads.
    """
    with np.load(path, allow_pickle=False) as payload:
        out = {"grid": None, "errors": {"available": False}, "pm_available": False}
        keys = set(payload.files)
        spectrum_keys = {"flux", "energy_lo_keV", "energy_hi_keV"}
        if "errors" in keys and not spectrum_keys <= keys:
            raise DatasetValidationError("Orphan uncertainty array without its spectrum/grid")
        if require_spectrum or keys & spectrum_keys:
            if not spectrum_keys <= keys:
                raise DatasetValidationError("Incomplete numerical spectral product")
            flux = np.asarray(payload["flux"], dtype=float)
            grid = inspect_energy_grid(payload["energy_lo_keV"], payload["energy_hi_keV"], expected_bins=expected_bins)
            if flux.shape != (grid["n_bins"],) or not np.isfinite(flux).all():
                raise DatasetValidationError("Invalid flux dimensions or non-finite flux")
            out.update(grid=grid, flux=flux)
            if "errors" in keys:
                out["errors"] = validate_uncertainties(flux, payload["errors"], flux_units=flux_units,
                    error_units=error_units, definition=error_definition, zero_policy=zero_policy)
                out["error_values"] = np.asarray(payload["errors"], dtype=float)
            elif require_errors:
                raise DatasetValidationError("Original spectral errors are unavailable")
        elif require_errors:
            raise DatasetValidationError("Errors cannot be verified without a spectrum")
        pm_keys = set(PARAMETER_COLUMNS)
        if require_pm or keys & pm_keys:
            if not pm_keys <= keys:
                raise DatasetValidationError("Incomplete PM parameter product")
            pm = np.asarray([payload[c].item() for c in PARAMETER_COLUMNS], dtype=float)
            if not np.isfinite(pm).all() or pm[0] <= 0 or (pm[2:] < 0).any():
                raise DatasetValidationError("Invalid PM parameter values")
            out.update(pm_available=True, pm=pm)
    return out
