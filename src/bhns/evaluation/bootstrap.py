"""Stratified source bootstrap, including paired differences on the same systems."""
import numpy as np
from bhns.evaluation.metrics import binary_metrics


def bootstrap_sources(source_rows,other=None,*,repetitions=2000,seed=42):
    if source_rows.source_id.duplicated().any():raise ValueError('Bootstrap input must have one row per physical source')
    source_rows=source_rows.sort_values('source_id').reset_index(drop=True)
    y=source_rows.true_class.eq('NS').astype(int).to_numpy();p=source_rows.p_NS.to_numpy()
    if other is not None:
        other=other.sort_values('source_id').reset_index(drop=True)
        if not source_rows.source_id.equals(other.source_id) or not source_rows.true_class.equals(other.true_class):raise ValueError('Paired comparison requires identical physical sources and labels')
        q=other.p_NS.to_numpy()
    strata=[np.flatnonzero(y==k) for k in [0,1]]
    if any(len(x)<2 for x in strata):raise ValueError('At least two independent sources per class for uncertainty')
    rng=np.random.default_rng(seed);samples=[]
    for _ in range(repetitions):
        idx=np.concatenate([rng.choice(s,len(s),replace=True) for s in strata]);m=binary_metrics(y[idx],p[idx])
        if other is not None:
            second=binary_metrics(y[idx],q[idx]);m={k:v-second[k] for k,v in m.items()}
        samples.append(m)
    return {k:dict(lower=float(np.quantile([m[k] for m in samples],.025)),upper=float(np.quantile([m[k] for m in samples],.975))) for k in samples[0]}
