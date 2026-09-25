"""Run only the frozen exploratory proxy diagnostic; never fit a matched model."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from bhns.data.state_validation import PROXY_FEATURES, spectral_coordinates
from bhns.experiments.state_validation import run_proxy

ROOT=Path(__file__).resolve().parents[1]

def load_proxy_frame(root=ROOT):
    raw=pd.read_csv(root/'data/processed/validation_heasoft/expanded_source_observations.csv')
    coords=pd.read_csv(root/'data/state_validation/spectral_regime_coordinates.csv')
    derived=spectral_coordinates(raw)
    assert coords.rxte_obsid.equals(derived.rxte_obsid)
    np.testing.assert_allclose(coords[PROXY_FEATURES],derived[PROXY_FEATURES],rtol=1e-12)
    frame=raw[['source_id','canonical_source','class_label','rxte_obsid','net_count_rate','observation_time']].rename(columns={'canonical_source':'source_name','class_label':'compact_object_class','rxte_obsid':'obs_id'}).copy()
    # Canonical flux columns satisfy the existing fold schema only. The estimator
    # receives the three-feature whitelist, never these 43 columns.
    for i in range(43):frame[f'flux_{i:02d}']=raw[f'spectrum_{i:02d}'].to_numpy()
    for c in PROXY_FEATURES:frame[c]=coords[c].to_numpy()
    return frame.loc[coords.proxy_valid].reset_index(drop=True)

def main():
    frame=load_proxy_frame()
    for model in ['logistic','forest']:
        for split in ['grouped','loso']:run_proxy(frame,ROOT,model,split)

if __name__=='__main__':main()
