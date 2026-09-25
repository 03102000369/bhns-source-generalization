"""Aggregate held-out probabilities with one independent row per physical source."""
import numpy as np
import pandas as pd
from scipy.special import expit,logit


def aggregate_sources(predictions):
    required={'source_id','source_name','obs_id','true_class','p_NS'}
    if required-set(predictions):raise ValueError('Missing prediction attribution')
    if predictions.obs_id.duplicated().any():raise ValueError('Aggregate one out-of-fold prediction per observation')
    if predictions.groupby('source_id').true_class.nunique().gt(1).any():raise ValueError('Conflicting source targets')
    if not predictions.p_NS.between(0,1).all():raise ValueError('Invalid probabilities')
    rows=[]
    for sid,g in predictions.groupby('source_id',sort=True):
        p=g.p_NS.to_numpy(float);target=int(g.true_class.iloc[0]=='NS')
        rows.append(dict(source_id=sid,source_name=g.source_name.iloc[0],true_class=g.true_class.iloc[0],
                         n_observations=len(g),p_NS=float(expit(logit(np.clip(p,1e-7,1-1e-7)).mean())),
                         mean_probability=float(p.mean()),std_probability=float(p.std()),minimum_probability=float(p.min()),maximum_probability=float(p.max()),
                         fraction_correct=float(np.mean((p>=.5)==target)),mean_signed_probability_error=float(p.mean()-target)))
    return pd.DataFrame(rows)
