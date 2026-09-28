"""Validation-only fits with explicit feature isolation and existing source folds."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from bhns.data.instrument_validation import META_FEATURES,SPECTRAL_FEATURES,validation_path,validation_protocol
from bhns.evaluation.splits import validate_fold,add_inner_validation,fold_definition,dataset_fingerprint
from bhns.experiments.core import outer_folds,estimator,candidate_parameters
from bhns.experiments.source_balancing import source_weights
from bhns.evaluation.aggregation import aggregate_sources
from bhns.evaluation.metrics import binary_metrics
from bhns.evaluation.bootstrap import bootstrap_sources

def matrix(frame,columns):
    if list(columns) not in [META_FEATURES,SPECTRAL_FEATURES]:raise ValueError('Features must match an explicitly allowed validation family')
    a=frame[list(columns)].to_numpy(float)
    if not np.isfinite(a).all():raise ValueError('Missing/nonfinite validation features; no unregistered imputation')
    return a

def predictions(frame,positions,p):
    out=frame.iloc[list(positions)][['source_id','source_name','obs_id','compact_object_class']].rename(columns={'compact_object_class':'true_class'}).copy()
    out['p_NS']=p;out['p_BH']=1-p;return out

def fit_fold(frame,fold,model,columns,seed=42,fixed=None):
    validate_fold(frame,fold);x=matrix(frame,columns);y=frame.compact_object_class.eq('NS').astype(int).to_numpy()
    params=candidate_parameters(model) if fixed is None else [fixed];scores=[];inner=None
    if len(params)>1:
        inner=add_inner_validation(frame,fold,validation_fraction=.2,seed=seed)
        a,b=list(inner.train),list(inner.validation);scaler=StandardScaler().fit(x[a]);xt=scaler.transform(x[a]);xv=scaler.transform(x[b])
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
        feature_columns=list(columns),scaler_mean=scaler.mean_.tolist(),scaler_scale=scaler.scale_.tolist(),
        feature_effect=imp.tolist(),effect_type='standardized_coefficient' if model=='logistic' else 'impurity_importance_not_causal')

def run_validation(frame,root,tag,model,mode,columns,seed=42,fixed=None,bootstrap=True):
    frame=frame.reset_index(drop=True);_,ph=validation_protocol(root);folder=validation_path(root,'results/validation_heasoft/runs/'+tag);folder.mkdir(parents=True,exist_ok=True)
    predpath=folder/'predictions.csv';summarypath=folder/'summary.json';fp=dataset_fingerprint(frame)
    if summarypath.exists():
        summary=json.loads(summarypath.read_text())
        if summary['protocol_sha256']!=ph or summary['dataset_fingerprint']!=fp:raise ValueError('Validation checkpoint mismatch')
        return pd.read_csv(predpath),summary,json.loads((folder/'fit_audits.json').read_text())
    pieces=[];audits=[]
    for fold in outer_folds(frame,mode,seed):
        pred,audit=fit_fold(frame,fold,model,columns,seed,fixed);pieces.append(pred);audits.append(audit)
    pred=pd.concat(pieces,ignore_index=True)
    if pred.obs_id.duplicated().any() or set(pred.obs_id)!=set(frame.obs_id):raise ValueError('Missing or duplicate validation predictions')
    sources=aggregate_sources(pred);metrics=binary_metrics(sources.true_class.eq('NS'),sources.p_NS)
    intervals=bootstrap_sources(sources,repetitions=2000,seed=seed) if bootstrap else {}
    summary=dict(tag=tag,model=model,split=mode,observations=len(frame),sources=len(sources),BH_sources=int(sources.true_class.eq('BH').sum()),NS_sources=int(sources.true_class.eq('NS').sum()),protocol_sha256=ph,dataset_fingerprint=fp,metrics=metrics,intervals=intervals)
    pred.to_csv(predpath,index=False);sources.to_csv(folder/'source_summary.csv',index=False)
    (folder/'fit_audits.json').write_text(json.dumps(audits,indent=2));summarypath.write_text(json.dumps(summary,indent=2))
    print(tag,'n=',len(frame),'AUROC=',round(metrics['AUROC'],4),flush=True)
    return pred,summary,audits
