"""Fold-bound preprocessing; all learned statistics use inner-training rows only."""

import numpy as np
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from bhns.data.schema import feature_columns
from bhns.evaluation.splits import validate_fold


class TrainingOnlyPreprocessor:
    """Fresh instance per fold. No fit method accepting an unpartitioned X array.

    Any later feature selection must be added inside this pipeline. Validation
    and test transformations never update statistics. There is no automatic
    fit-on-all-data refit path in the Gates 0–2 implementation.
    """

    def __init__(self, representation="SM", *, imputation=None, standardize=True,
                 pca_components=None, seed=42):
        self.columns = feature_columns(representation)
        if imputation not in (None, "median"):
            raise ValueError("Only explicit median imputation or no imputation is supported")
        self.imputation = imputation
        self.standardize = standardize
        self.pca_components = pca_components
        self.seed = seed

    def _matrix(self, frame):
        missing = set(self.columns) - set(frame)
        if missing:
            raise ValueError(f"Representation is unavailable; missing {sorted(missing)}")
        values = frame[list(self.columns)].to_numpy(dtype=float, na_value=np.nan)
        if np.isinf(values).any():
            raise ValueError("Infinite features cannot be preprocessed")
        if self.imputation is None and np.isnan(values).any():
            raise ValueError("Missing features require an explicit training-only imputation policy")
        return values

    def fit(self, frame, fold):
        if hasattr(self, "pipeline_"):
            raise RuntimeError("Create a fresh preprocessor for each fold; refitting is forbidden")
        validate_fold(frame, fold)
        training = frame.iloc[list(fold.train)]
        matrix = self._matrix(training)
        if np.isnan(matrix).all(axis=0).any():
            raise ValueError("An all-missing training feature cannot be learned from held-out data")
        steps = []
        if self.imputation:
            steps.append(("imputer", SimpleImputer(strategy=self.imputation)))
        if self.standardize:
            steps.append(("scaler", StandardScaler()))
        if self.pca_components is not None:
            steps.append(("pca", PCA(n_components=self.pca_components, random_state=self.seed)))
        pipeline = Pipeline(steps or [("identity", "passthrough")])
        pipeline.fit(matrix)
        self.pipeline_ = pipeline
        self.fold_ = fold
        self.fit_obs_ids_ = tuple(training.obs_id)
        self.fit_source_ids_ = tuple(sorted(training.source_id.unique()))
        return self

    def transform(self, frame, *, partition):
        if not hasattr(self, "pipeline_"):
            raise RuntimeError("Fit on a validated training fold first")
        if partition not in {"train", "validation", "test"}:
            raise ValueError("partition must be train, validation or test")
        validate_fold(frame, self.fold_)
        positions = getattr(self.fold_, partition)
        if not positions:
            raise ValueError(f"The {partition} partition is empty")
        return self.pipeline_.transform(self._matrix(frame.iloc[list(positions)]))
