"""Source-disjoint proxy diagnostic with isolated state-stage outputs."""
import json
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from bhns.data.state_validation import PROXY_FEATURES, feature_matrix as matrix, sha256, verify_protected
from bhns.evaluation.splits import validate_fold,add_inner_validation,fold_definition,dataset_fingerprint
from bhns.experiments.core import outer_folds,estimator,candidate_parameters
from bhns.experiments.source_balancing import source_weights
from bhns.evaluation.aggregation import aggregate_sources
from bhns.evaluation.metrics import binary_metrics
from bhns.evaluation.bootstrap import bootstrap_sources
from bhns.experiments.instrument_validation import predictions

def fit_fold(frame,fold,model,columns,seed=42,fixed=None):
    validate_fold(frame,fold);x=matrix(frame,columns);y=frame.compact_object_class.eq('NS').astype(int).to_numpy()
    params=candidate_parameters(model) if fixed is None else [fixed];scores=[];inner=None
    if len(params)>1:
        inner=add_inner_validation(frame,fold,validation_fraction=.2,seed=seed)
        a,b=list(inner.train),list(inner.validation);scaler=StandardScaler().fit(x[a]);xt=scaler.transform(x[a]);xv=scaler.transform(x[b]);inner_mean=scaler.mean_.tolist()
        for param in params:
            clf=estimator(model,param,seed);clf.fit(xt,y[a],sample_weight=source_weights(frame.iloc[a]))
            src=aggregate_sources(predictions(frame,b,clf.predict_proba(xv)[:,1]));scores.append(binary_metrics(src.true_class.eq('NS'),src.p_NS)['balanced_accuracy'])
        chosen=params[int(np.argmax(scores))]
    else:chosen=params[0]
    a,b=list(fold.train),list(fold.test);scaler=StandardScaler().fit(x[a]);clf=estimator(model,chosen,seed)
    clf.fit(scaler.transform(x[a]),y[a],sample_weight=source_weights(frame.iloc[a]));p=clf.predict_proba(scaler.transform(x[b]))[:,1]
    imp=clf.coef_[0] if model=='logistic' else clf.feature_importances_
    return predictions(frame,b,p),dict(parameters=chosen,selection_scores=scores,
        outer=fold_definition(frame,fold),inner=None if inner is None else fold_definition(frame,inner),
        fit_obs_ids=frame.iloc[a].obs_id.tolist(),fit_source_ids=sorted(frame.iloc[a].source_id.unique()),
        feature_columns=list(columns),inner_scaler_mean=None if inner is None else inner_mean,scaler_mean=scaler.mean_.tolist(),scaler_scale=scaler.scale_.tolist(),
        feature_effect=imp.tolist(),effect_type='standardized_coefficient' if model=='logistic' else 'impurity_importance_not_causal')


def run_proxy(frame,root,model,mode):
    root=Path(root)
    frozen=json.loads((root/'results/state_validation/frozen_manifest.json').read_text())
    verify_protected(root,frozen)
    verify_protected(root,json.loads((root/'results/state_validation/protected_artifact_manifest.json').read_text()))
    protocol=json.loads((root/'configs/state_validation_protocol_frozen.yaml').read_text())
    assert protocol['secondary_proxy_diagnostic']['enabled']
    folder=root/'results/state_validation/runs'/f'PROXY_ONLY_{model}_{mode}'
    if folder.exists():raise ValueError('State run exists; frozen outputs cannot be overwritten')
    folder.mkdir(parents=True)
    started=datetime.now(timezone.utc).isoformat()
    pieces=[];audits=[]
    for fold in outer_folds(frame,mode,42):
        pred,audit=fit_fold(frame,fold,model,PROXY_FEATURES);pieces.append(pred);audits.append(audit)
    pred=pd.concat(pieces,ignore_index=True)
    if pred.obs_id.duplicated().any() or set(pred.obs_id)!=set(frame.obs_id):raise ValueError('Incomplete or duplicate predictions')
    sources=aggregate_sources(pred);metrics=binary_metrics(sources.true_class.eq('NS'),sources.p_NS)
    summary=dict(tag=folder.name,analysis='exploratory_spectral_regime_proxy_diagnostic_not_state_matched',
       model=model,split=mode,observations=len(frame),sources=len(sources),BH_sources=int(sources.true_class.eq('BH').sum()),NS_sources=int(sources.true_class.eq('NS').sum()),
       protocol_sha256=sha256(root/'configs/state_validation_protocol_frozen.yaml'),dataset_fingerprint=dataset_fingerprint(frame),
       started_utc=started,completed_utc=datetime.now(timezone.utc).isoformat(),metrics=metrics,intervals=bootstrap_sources(sources,repetitions=2000,seed=42))
    pred.to_csv(folder/'predictions.csv',index=False);sources.to_csv(folder/'source_summary.csv',index=False)
    (folder/'fit_audits.json').write_text(json.dumps(audits,indent=2));(folder/'summary.json').write_text(json.dumps(summary,indent=2))
    print(folder.name,metrics,flush=True)
    return summary
