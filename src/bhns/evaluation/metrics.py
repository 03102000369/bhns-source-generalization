"""Binary metrics; NS is the explicitly recorded positive class."""
import numpy as np
from sklearn.metrics import roc_auc_score,average_precision_score


def binary_metrics(y,probability):
    y=np.asarray(y,int);p=np.asarray(probability,float)
    if y.shape!=p.shape or not np.isfinite(p).all() or np.any((p<0)|(p>1)) or not set(y)<={0,1}:
        raise ValueError('Invalid binary targets/probabilities')
    if len(set(y))!=2:raise ValueError('Both classes required for comparative binary metrics')
    pred=p>=.5;tp=np.sum(pred&(y==1));tn=np.sum(~pred&(y==0));fp=np.sum(pred&(y==0));fn=np.sum(~pred&(y==1))
    denominator=np.sqrt(float((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn)))
    return dict(AUROC=float(roc_auc_score(y,p)),balanced_accuracy=float(.5*(tp/(tp+fn)+tn/(tn+fp))),
                MCC=float((tp*tn-fp*fn)/denominator) if denominator else 0.,
                F1=float(2*tp/(2*tp+fp+fn)) if 2*tp+fp+fn else 0.,
                precision=float(tp/(tp+fp)) if tp+fp else 0.,recall=float(tp/(tp+fn)),
                PR_AUC=float(average_precision_score(y,p)),Brier=float(np.mean((y-p)**2)),accuracy=float(np.mean(pred==y)))
