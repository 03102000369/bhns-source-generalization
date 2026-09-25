"""Resolve pilot goodness-of-fit Monte Carlo precision; preserve initial run."""
from pathlib import Path
from paths import resolve_product_path, pilot_output
from evidence import sha256
import json,numpy as np
from scipy.stats import beta,chi2
from x1_validation import ROOT,forbid_x2_without_x1
from x2_measurement import Measurement,serialize
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main():
    gate=json.loads((ROOT/'reports/gate_x1_report.json').read_text())
    forbid_x2_without_x1(gate)
    out=pilot_output();p=out/'measurement_validation.json';record=json.loads(p.read_text());archive=out/'measurement_validation_initial96.json'
    if not archive.exists():archive.write_bytes(p.read_bytes())
    record['monte_carlo_precision_addendum']=dict(repeats=399,seed=240924,reason='Initial 96-draw plus-one p-value cannot resolve the predeclared p<0.01 diagnostic. Increase simulation precision without changing the criterion, continuum or features.')
    (out/'monte_carlo_precision_addendum.json').write_text(json.dumps(record['monte_carlo_precision_addendum'],indent=2)+'\n')
    rng=np.random.default_rng(240924);fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    for rec,ax in zip(record['modules'],axes.ravel()):
        obs=rec['obsid'];m=rec['module'][-1];directory='products_bright' if obs=='30363002002' else 'products';stem=f'nu{obs}{m}01'
        accepted=next(x for x in gate['modules'] if x['obsid']==obs and x['module']==rec['module'])
        paths={k:resolve_product_path(v) for k,v in accepted['paths'].items()}
        if any(sha256(p)!=accepted['hashes'][k] for k,p in paths.items()):raise ValueError('X1 product checksum mismatch')
        model=Measurement(paths);fit=rec['fit'];mu=np.asarray(fit['model_counts'])+model.alpha*np.asarray(fit['profile_background']);bg=np.asarray(fit['profile_background']);samples=[];dev=[];failed=0
        center=np.asarray(model.group@model.energy).ravel()/np.asarray(model.group.sum(axis=1)).ravel()
        residual=(model.source-mu)/np.sqrt(mu+model.alpha**2*bg)
        ax.axhline(0,c='black',lw=.8);ax.axhline(3,c='grey',ls=':',lw=.7);ax.axhline(-3,c='grey',ls=':',lw=.7);ax.plot(center,residual,'o',ms=2)
        ax.set(xlabel='Channel energy (keV)',ylabel='Approximate source residual / statistical σ',title=f'{obs} FPM{m}: deviance {fit["deviance"]:.1f}, nominal dof {fit["nominal_dof"]}',xlim=(5,25))
        for _ in range(399):
            model.source=rng.poisson(mu).astype(float);model.background=rng.poisson(bg).astype(float)
            try:t=model.fit(np.asarray(fit['theta']));samples.append(t['flux']);dev.append(t['deviance'])
            except ValueError:failed+=1
        k=int(np.sum(np.asarray(dev)>=fit['deviance']));n=len(dev);pv=(k+1)/(n+1)
        rec['bootstrap_refined']=dict(repeats=399,successful=n,failed=failed,exceedances=k,conditional_gof_p=pv,binomial_95_interval=[0 if k==0 else float(beta.ppf(.025,k,n-k+1)),1 if k==n else float(beta.ppf(.975,k+1,n-k))],asymptotic_chi2_p_diagnostic=float(chi2.sf(fit['deviance'],fit['nominal_dof'])),flux_sigma=np.std(samples,axis=0,ddof=1).tolist(),relative_mean_flux_bias=(np.mean(samples,axis=0)/np.asarray(fit['flux'])-1).tolist())
        if pv<.01:rec['flags'].append('STRUCTURED_RESIDUAL_OR_MODEL_MISFIT')
        if failed:rec['flags'].append('REFINED_BOOTSTRAP_FIT_FAILURE')
        print(obs,m,rec['bootstrap_refined'],'flags',rec['flags'],flush=True)
        (out/f'{obs}_{m}_measurement.json').write_text(json.dumps(rec,default=serialize,indent=2)+'\n')
    fig.suptitle('Locked continuum: independent NuSTAR module fit diagnostics');fig.savefig(out/'continuum_residuals.png',dpi=150);plt.close(fig)
    record['reason']='Locked continuum has poor fit diagnostics in the pilot; a label-blind measurement-design revision and module normalization convention are required before scaling.'
    p.write_text(json.dumps(record,default=serialize,indent=2)+'\n')
if __name__=='__main__':main()
