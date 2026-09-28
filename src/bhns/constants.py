"""Schema constants, never evidence that a dataset is correct."""

N_SPECTRAL_BINS = 43
CLASS_ENCODING = {"BH": 0, "NS": 1}
FLUX_COLUMNS = tuple(f"flux_{i:02d}" for i in range(N_SPECTRAL_BINS))
ERROR_COLUMNS = tuple(f"err_{i:02d}" for i in range(N_SPECTRAL_BINS))
PARAMETER_COLUMNS = ("kT", "Gamma", "Fbb_Fpl", "chi2_red", "variance_proxy")
IDENTITY_COLUMNS = ("source_id", "source_name", "compact_object_class", "obs_id")
MANIFEST_COLUMNS = (
    "source_id", "source_name", "compact_object_class", "n_observations",
    "label_reference", "label_status", "notes",
)
PROVENANCE_COLUMNS = tuple(c for c in MANIFEST_COLUMNS if c != "n_observations")
OBSERVATION_WARNING = "OBSERVATION-WISE — NOT SOURCE-INDEPENDENT"
