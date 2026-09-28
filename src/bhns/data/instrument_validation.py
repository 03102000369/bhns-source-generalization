"""Isolated instrumental sensitivity data; never writes a primary artifact."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from astropy.io import fits
from bhns.data.rxte_products import sha256,read_pha,net_ogip,rebin_rates,ENERGY_EDGES

META_FEATURES=['observation_year','log_exposure','num_selected_pcus']+[f'pcu{i}_selected' for i in range(5)]+['native_channels_used','native_min_keV','native_max_keV']+[f'gain_epoch_{i}' for i in range(1,6)]
SPECTRAL_FEATURES=[f'flux_{i:02d}' for i in range(43)]
EPOCH_STARTS=['1996-03-21T18:34:00','1996-04-15T23:06:00','1999-03-22T17:39:00','2000-05-13T00:00:00']

def verify_primary(root):
    root=Path(root);manifest=json.loads((root/'results/validation_heasoft/primary_immutability_manifest.json').read_text())
    changed=[p for p,h in manifest.items() if not (root/p).exists() or sha256(root/p)!=h]
    if changed:raise ValueError(f'Protected primary artifacts changed: {changed[:5]}')
    return len(manifest)

def validation_path(root,relative):
    root=Path(root).resolve();p=(root/relative).resolve()
    allowed=[(root/d/'validation_heasoft').resolve() for d in ['data/processed','data/provenance','data/raw','results','reports']]
    if not any(p==a or a in p.parents for a in allowed):raise ValueError('Output must be inside a validation directory')
    p.parent.mkdir(parents=True,exist_ok=True);return p

def validation_protocol(root):
    import yaml
    p=Path(root)/'configs/validation_heasoft_protocol.yaml'
    digest=sha256(p)
    if digest!=p.with_suffix('.sha256').read_text().strip():raise ValueError('Frozen validation protocol changed')
    return yaml.safe_load(p.read_text()),digest

def gain_epoch(date):
    t=pd.Timestamp(date)
    if pd.isna(t) or t<pd.Timestamp('1995-12-30') or t>pd.Timestamp('2012-01-06T23:59:59'):raise ValueError('Outside RXTE mission date range')
    return 1+sum(t>=pd.Timestamp(x) for x in EPOCH_STARTS)

def screening_expression(epoch):
    e='(ELV > 10) .AND. (OFFSET < 0.02) .AND. (PCU2_ON == 1) .AND. (ELECTRON2 < 0.1)'
    if epoch<=2:e+=' .AND. (TIME_SINCE_SAA > 30 .OR. TIME_SINCE_SAA < 0)'
    return e

def detector_samples(filter_path,starts,stops,epoch):
    with fits.open(filter_path,memmap=False) as h:
        d=h[1].data;t=np.asarray(d['Time'],float)+float(h[1].header.get('TIMEZERO',0));inside=np.zeros(len(t),bool)
        for a,b in zip(starts,stops):inside|=(t>=a)&(t<b)
        if not inside.any():raise ValueError('No filter samples within spectrum GTIs')
        states=np.column_stack([np.asarray(d[f'PCU{i}_ON'],float) for i in range(5)])
        sampled=states[inside];valid=np.isfinite(sampled)&np.isin(sampled,[0,1])
        frac=np.divide(np.where(valid,sampled,0).sum(axis=0),valid.sum(axis=0),out=np.full(5,np.nan),where=valid.sum(axis=0)>0)
        def col(name):return np.asarray(d[name],float)
        mask=(col('ELV')>10)&(col('OFFSET')<.02)&(states[:,2]==1)&(col('ELECTRON2')<.1)
        if epoch<=2:
            s=col('TIME_SINCE_SAA');mask&=(s>30)|(s<0)
        width=float(h[1].header.get('TIMEDEL',np.median(np.diff(t))))
        # Diagnostic quadrature only; actual new spectra require maketime/re-extraction.
        overlap=np.zeros(len(t));pixel=float(h[1].header.get('TIMEPIXR',.5))
        for a,b in zip(starts,stops):overlap+=np.maximum(0,np.minimum(t+(1-pixel)*width,b)-np.maximum(t-pixel*width,a))
        return dict(active_pcus='|'.join(str(i) for i in range(5) if frac[i]>0),
                    num_active_pcus=float(np.nansum(frac)),active_pcu_fractions=frac.tolist(),
                    filter_sample_count=int(inside.sum()),screening_sample_fraction=float(mask[inside].mean()),
                    sampled_gti_seconds=float(overlap.sum()),screening_retained_seconds_estimate=float(overlap[mask].sum()),
                    screening_exposure_removed_estimate=float(overlap[~mask].sum()))

def primary_confounders(root):
    root=Path(root);f=pd.read_csv(root/'data/processed/observations.csv');f=f[f.usable].copy();rows=[]
    for r in f.to_dict('records'):
        p=json.loads((root/r['provenance_path']).read_text());m=p['metadata'];files={x['product_type']:x['path'] for x in p['inputs']}
        s=read_pha(files['source']);epoch=gain_epoch(r['observation_time']);t=pd.Timestamp(r['observation_time'])
        row={k:r[k] for k in ['rxte_obsid','source_id','canonical_source','class_label','observation_time','exposure','net_count_rate','source_count_rate','background_count_rate','grid_id']}
        row.update(selected_pcus=r['pcus'],num_selected_pcus=len(m['pcus']),gain_epoch=epoch,
                   observation_year=t.year+(t.dayofyear-1)/365.25,log_exposure=float(np.log(r['exposure'])),
                   background_fraction=r['background_count_rate']/r['source_count_rate'],
                   native_channels_used=m['native_channels_used'],native_min_keV=m['native_min_keV'],native_max_keV=m['native_max_keV'],
                   response_identifier=m['response_metadata']['calibration_identifier'],response_creator=m['response_metadata']['creator'],
                   source_product_sha256=sha256(files['source']),deadtime_status=r['deadtime_status'])
        row.update({f'pcu{i}_selected':int(i in m['pcus']) for i in range(5)})
        row.update({f'gain_epoch_{i}':int(epoch==i) for i in range(1,6)})
        row.update(detector_samples(files['filter'],s['starts'],s['stops'],epoch));row['active_pcu_fractions']=json.dumps(row['active_pcu_fractions'])
        rows.append(row)
    result=pd.DataFrame(rows)
    if result.rxte_obsid.duplicated().any() or not np.isfinite(result[META_FEATURES].to_numpy(float)).all():raise ValueError('Invalid confounder matrix')
    return result

def common_support(frame):
    """Frozen restriction: defined without predictions; retains exact detector/epoch support."""
    base=frame[frame.exposure.between(256,16384)&frame.net_count_rate.between(5,1000,inclusive='right')&frame.background_fraction.le(.5)].copy()
    cols=['gain_epoch','selected_pcus'];counts=base.groupby(cols+['class_label']).source_id.nunique().unstack(fill_value=0)
    if not {'BH','NS'}<=set(counts):return base.iloc[:0].copy()
    accepted=counts[(counts.BH>=2)&(counts.NS>=2)].reset_index()[cols]
    result=base.merge(accepted,on=cols,validate='many_to_one')
    # Repeat after pruning low-observation sources so admitted strata remain supported.
    while len(result):
        old=set(result.rxte_obsid);good=result.groupby('source_id').size();result=result[result.source_id.isin(good[good>=2].index)]
        c=result.groupby(cols+['class_label']).source_id.nunique().unstack(fill_value=0)
        if not {'BH','NS'}<=set(c):return result.iloc[:0].copy()
        result=result.merge(c[(c.BH>=2)&(c.NS>=2)].reset_index()[cols],on=cols,validate='many_to_one')
        if set(result.rxte_obsid)==old:break
    return result.sort_values('rxte_obsid').reset_index(drop=True)

def shape_normalize(values):
    a=np.asarray(values,float);total=a.sum(axis=1)
    if not np.isfinite(a).all() or np.any(total<=0):raise ValueError('Shape normalization requires finite positive band sum')
    return a/total[:,None]

def heasoft_spectrum(source_path,background_path,response_path):
    """pcaextspect2 rates are already per live detector; never divide by nPCU again."""
    s=read_pha(source_path);b=read_pha(background_path);net,var,bg=net_ogip(s,b)
    if s['pcus']!=[2] or b['pcus']!=[2]:raise ValueError('Validation spectrum is not restricted to PCU2')
    if s['starts'].shape!=b['starts'].shape or not np.allclose(s['starts'],b['starts'],atol=1e-6,rtol=0) or not np.allclose(s['stops'],b['stops'],atol=1e-6,rtol=0):raise ValueError('HEASoft source/background GTIs differ')
    with fits.open(response_path,memmap=False) as h:
        e=h['EBOUNDS'];low=np.asarray(e.data['E_MIN'],float);high=np.asarray(e.data['E_MAX'],float)
        if not np.array_equal(s['channels'],e.data['CHANNEL']):raise ValueError('HEASoft response channel mismatch')
        matrix=h['SPECRESP MATRIX'] if 'SPECRESP MATRIX' in h else h['MATRIX']
        vals=np.concatenate([np.asarray(x,float).ravel() for x in matrix.data['MATRIX']])
        if not np.isfinite(vals).all() or np.any(vals<0) or not np.any(vals>0):raise ValueError('Invalid response')
    spec,cov,w=rebin_rates(net,var,low,high)
    if cov is None:raise ValueError('No statistical uncertainty recovered')
    used=w.sum(axis=0)>0
    if np.any(s['quality'][used]!=0) or np.any(b['quality'][used]!=0):raise ValueError('Bad channels in validation band')
    return dict(spectrum=spec,error=np.sqrt(np.diag(cov)),covariance=cov,native_low_keV=low,native_high_keV=high,native_net_rate=net,native_variance=var,overlap_weights=w,energy_edges_keV=ENERGY_EDGES),dict(exposure=float(s['header']['EXPOSURE']),source_count_rate=float((w@s['rate']).sum()),background_count_rate=float((w@bg).sum()),net_count_rate=float(spec.sum()),source_header=str(s['header']),background_header=str(b['header']))
