"""Execute only the two-observation, independent-module measurement audit."""
from pathlib import Path
from paths import resolve_product_path, pilot_output
from datetime import datetime,timezone
import csv,json,sys
import numpy as np
from x1_validation import ROOT,forbid_x2_without_x1,sha
from x2_measurement import Measurement,features,serialize,NODES

def main():
    gate=json.loads((ROOT/'reports/gate_x1_report.json').read_text());forbid_x2_without_x1(gate)
    out=pilot_output();out.mkdir(parents=True,exist_ok=True)
    if (out/'measurement_validation.json').exists():raise ValueError('Use a fresh BHNS_X2_OUTPUT directory')
    settings=dict(written_before_fits_utc=datetime.now(timezone.utc).isoformat(),locked_protocol_sha256=sha(ROOT/'configs/cross_mission_protocol.yaml'),primary_grouping_min_background_counts=5,diagnostic_grouping_counts=[1,10],bootstrap_repeats=96,seed=240923,guard_sensitivity_limits_keV=[3,40],area_sensitivity=dict(uniform_scale=1.03,tilt_exponent=.03,note='Illustrative stress tests, not an official calibration uncertainty'),investigation_flags=dict(bootstrap_gof_p_below=.01,band_difference_sigma_above=3,grouping_or_guard_flux_change_fraction_above=.05),module_combination='None; normalization anchor is not frozen',class_labels_read=False)
    (out/'pilot_settings.json').write_text(json.dumps(settings,indent=2)+'\n')
    rng=np.random.default_rng(settings['seed']);records=[]
    for rec in gate['modules']:
        obs=rec['obsid'];m=rec['module'][-1];directory='products_bright' if obs=='30363002002' else 'products'
        paths={k:resolve_product_path(v) for k,v in rec['paths'].items()}
        if any(sha(p)!=rec['hashes'][k] for k,p in paths.items()):raise ValueError('Local product hash differs from accepted X1 product')
        measurement=Measurement(paths);fit=measurement.fit();f=features(fit['flux'],fit['flux_covariance']);result=dict(obsid=obs,module=rec['module'],input_hashes=rec['hashes'],fit=fit,features=f)
        print(obs,m,'fit',fit['deviance'],fit['nominal_dof'],fit['flux'],flush=True)
        source,background=measurement.source.copy(),measurement.background.copy();samples=[];dev=[];failures=0
        for _ in range(settings['bootstrap_repeats']):
            measurement.source=rng.poisson(fit['model_counts']+measurement.alpha*fit['profile_background']).astype(float);measurement.background=rng.poisson(fit['profile_background']).astype(float)
            try:
                trial=measurement.fit(fit['theta']);samples.append(trial['flux']);dev.append(trial['deviance'])
            except ValueError:failures+=1
        measurement.source,measurement.background=source,background
        samples=np.asarray(samples);p=(1+np.sum(np.asarray(dev)>=fit['deviance']))/(len(dev)+1)
        result['bootstrap']=dict(repeats=settings['bootstrap_repeats'],failed_fits=failures,flux_sigma=np.std(samples,axis=0,ddof=1),flux_percentiles_16_84=np.percentile(samples,[16,84],axis=0),relative_mean_bias=np.mean(samples,axis=0)/fit['flux']-1,conditional_gof_p=float(p),gof_mc_standard_error=float(np.sqrt(p*(1-p)/(len(dev)+1))),note='Conditional parametric bootstrap under fitted grouped background; not full cohort uncertainty coverage')
        variants={}
        for name,kwargs in [('group1',dict(min_background=1)),('group10',dict(min_background=10)),('guard3_40',dict(guard_limits=(3,40))),('area_plus3percent',dict(area_scale=1.03)),('area_tilt',dict(area_tilt=.03))]:
            v=Measurement(paths,**kwargs).fit(fit['theta']);variants[name]=dict(flux=v['flux'],relative_flux_change=v['flux']/fit['flux']-1,deviance=v['deviance'],bound_contact=v['bound_contact'])
        result['sensitivity']=variants
        # Noiseless class-independent closure through each actual response.
        closure=[]
        for slope in [1.5,2.5,4.]:
            theta=np.log(np.exp(fit['theta'][1]))-slope*np.log(NODES/8);model,_=measurement.expected(theta)
            measurement.source=model+measurement.alpha*fit['profile_background'];measurement.background=fit['profile_background'].copy()
            recovered=measurement.fit();truth=measurement.flux(theta)[0]
            closure.append(dict(photon_index=slope,max_absolute_relative_band_bias=float(np.max(abs(recovered['flux']/truth-1)))))
        measurement.source,measurement.background=source,background;result['noiseless_response_closure']=closure
        result['flags']=[]
        if fit['bound_contact']:result['flags'].append('CONTINUUM_BOUND_CONTACT')
        if p<.01:result['flags'].append('STRUCTURED_RESIDUAL_OR_MODEL_MISFIT')
        if failures:result['flags'].append('BOOTSTRAP_FIT_FAILURE')
        if any(np.max(np.abs(variants[n]['relative_flux_change']))>.05 for n in ['group1','group10','guard3_40']):result['flags'].append('BINNING_OR_GUARD_SENSITIVITY')
        records.append(result);(out/f'{obs}_{m}_measurement.json').write_text(json.dumps(result,default=serialize,indent=2)+'\n')
        print(obs,m,'bootstrap p',p,'flags',result['flags'],flush=True)
    comparisons=[]
    for obs in sorted({r['obsid'] for r in records}):
        a,b=[next(r for r in records if r['obsid']==obs and r['module']==m) for m in ['FPMA','FPMB']]
        for family in ['flux','A','B','C','total_observed_flux']:
            if family=='total_observed_flux':
                va,vb=[np.array([np.sum(r['fit']['flux'])]) for r in [a,b]]
                sa,sb=[np.array([np.sqrt(np.sum(r['fit']['flux_covariance']))]) for r in [a,b]]
            else:
                va=np.asarray(a['fit']['flux'] if family=='flux' else a['features'][family]['values']);vb=np.asarray(b['fit']['flux'] if family=='flux' else b['features'][family]['values'])
                sa=np.asarray(a['fit']['flux_sigma'] if family=='flux' else a['features'][family]['sigma']);sb=np.asarray(b['fit']['flux_sigma'] if family=='flux' else b['features'][family]['sigma'])
            for i in range(len(va)):
                sigma=float(np.hypot(sa[i],sb[i]));z=float((vb[i]-va[i])/sigma)
                comparisons.append(dict(obsid=obs,family=family,coordinate=i,fpma=float(va[i]),fpmb=float(vb[i]),fpma_sigma=float(sa[i]),fpmb_sigma=float(sb[i]),difference_sigma=z,fpmb_over_fpma=float(vb[i]/va[i]) if family in ['flux','B','total_observed_flux'] else '',status='REVIEW' if abs(z)>3 else 'NO_3SIGMA_FLAG',uncertainty='Statistical only; shared/relative calibration errors not included'))
    with (out/'fpma_fpmb_feature_comparison.csv').open('w') as f:w=csv.DictWriter(f,fieldnames=comparisons[0]);w.writeheader();w.writerows(comparisons)
    result=dict(scientific_status='NOT_YET_TESTED',gate_x1='PASS',gate_x2='NOT PASSED',pilot_status='X2_PILOT_NEEDS_REVISION',reason='Module normalization convention remains unfrozen; inspect fit/sensitivity/module flags before scaling',settings=settings,modules=records,comparison_flags=sum(r['status']=='REVIEW' for r in comparisons))
    (out/'measurement_validation.json').write_text(json.dumps(result,default=serialize,indent=2)+'\n')
    print('X2_PILOT_NEEDS_REVISION; no cohort or classification run',flush=True)

if __name__=='__main__':main()
