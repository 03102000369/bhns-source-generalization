"""Read-only FITS audit of screening, detector, background and deadtime provenance."""
from pathlib import Path
import json,re
import numpy as np
import pandas as pd
from astropy.io import fits
from bhns.data.instrument_validation import *
ROOT=Path(__file__).resolve().parents[1]

def union(intervals):
    merged=[]
    for a,b in sorted(intervals):
        if b<=a:continue
        if merged and a<=merged[-1][1]:merged[-1][1]=max(b,merged[-1][1])
        else:merged.append([a,b])
    return merged

def duration(intervals):return sum(b-a for a,b in union(intervals))

def main():
    verify_primary(ROOT);rows=[];histories=[];caldb=Path(json.loads((ROOT/'results/validation_heasoft/software_environment.json').read_text())['caldb']['root'])
    with fits.open(caldb/'data/xte/pca/caldb.indx') as h:
        candidates={str(r['CAL_FILE']) for r in h[1].data if r['CAL_CNAM']=='PCA_BKGD_MODEL' and r['CAL_QUAL']==0}
    # This release has exactly one good background file. The old FTOOL truncates
    # long HISTORY paths, so resolve its identity against the frozen CALDB index.
    if len(candidates)!=1:raise ValueError('Background identity requires review: multiple good calibration files')
    model=next(iter(candidates));modelpath=next(caldb.rglob(model));modelhash=sha256(modelpath)
    selections=pd.concat([pd.read_csv(ROOT/'data/processed/validation_heasoft/preselected_observations.csv'),pd.read_csv(ROOT/'data/processed/validation_heasoft/expanded_selection.csv')]).set_index('rxte_obsid')
    for path in sorted((ROOT/'data/processed/validation_heasoft/reduction').glob('*/processing.json')):
        rec=json.loads(path.read_text());folder=path.parent;obs=rec['rxte_obsid'];row=selections.loc[obs]
        out=dict(rxte_obsid=obs,source_id=rec['source_id'],source=rec['source_name'],class_label=rec['class_label'],status=rec['status'],observation_time=row.observation_time,gain_epoch=gain_epoch(row.observation_time),selected_pcus='2')
        raw_intervals=[]
        for raw in (ROOT/'data/raw/validation_heasoft'/obs/'pca').glob('FS4a*'):
            with fits.open(raw) as h:
                width=float(h[1].header['TIMEDEL']);pixel=float(h[1].header.get('TIMEPIXR',0));t=h[1].data['Time']+float(h[1].header.get('TIMEZERO',0))-pixel*width;raw_intervals.extend(zip(t,t+width))
        raw_intervals=union(raw_intervals);out['raw_standard2_row_coverage_seconds']=duration(raw_intervals)
        if (folder/'screened.gti').exists():
            with fits.open(folder/'screened.gti') as h:
                zero=float(h[1].header.get('TIMEZERO',0));gti=list(zip(h[1].data['START']+zero,h[1].data['STOP']+zero))
            out['screened_gti_seconds']=duration(gti)
            out['screened_raw_overlap_seconds']=duration([(max(a,c),min(b,d)) for a,b in raw_intervals for c,d in gti if min(b,d)>max(a,c)])
            out['screening_removed_raw_coverage_seconds']=out['raw_standard2_row_coverage_seconds']-out['screened_raw_overlap_seconds']
        if rec['status']=='COMPLETE':
            s=read_pha(folder/'source.pha');b=read_pha(folder/'background.pha');sh=s['header'];bh=b['header']
            out.update(exposure=sh['EXPOSURE'],ontime=sh['ONTIME'],background_exposure=bh['EXPOSURE'],source_deadapp=bool(sh.get('DEADAPP')),background_deadapp=bool(bh.get('DEADAPP')),deadtime_fraction=1-sh['EXPOSURE']/sh['ONTIME'],deadtime_rate_factor=sh['ONTIME']/sh['EXPOSURE'],source_count_rate=rec['metadata']['source_count_rate'],background_count_rate=rec['metadata']['background_count_rate'],net_rate=rec['metadata']['net_count_rate'])
            out['background_fraction']=out['background_count_rate']/out['source_count_rate']
            out['source_rate_without_deadtime_correction']=out['source_count_rate']*sh['EXPOSURE']/sh['ONTIME']
            if not out['source_deadapp'] or not out['background_deadapp'] or not 0<=out['deadtime_fraction']<1:raise ValueError(f'Invalid recorded deadtime correction: {obs}')
            filt=folder/(folder/'prepared/FP_xtefilt.lis').read_text().strip()
            out.update(detector_samples(filt,s['starts'],s['stops'],out['gain_epoch']))
            out['active_pcu_fractions']=json.dumps(out['active_pcu_fractions'])
            with fits.open(folder/'response.rsp') as h:
                out.update(response_sha256=sha256(folder/'response.rsp'),response_creator=h[1].header.get('CREATOR'),native_channels=len(h['EBOUNDS'].data),native_min_keV=float(h['EBOUNDS'].data['E_MIN'].min()),native_max_keV=float(h['EBOUNDS'].data['E_MAX'].max()))
            par=(folder/'pfiles/pcabackest.par').read_text();match=re.search(r'modelfamily,s,h,"([^"]+)"',par)
            out.update(background_family=match.group(1) if match else 'UNKNOWN',background_model=model,background_model_sha256=modelhash,background_resolution='Unique CAL_QUAL=0 PCA_BKGD_MODEL in frozen CALDB, combined with recorded extension HISTORY')
            for p in sorted((folder/'prepared').glob('*_bkg')):
                with fits.open(p) as h:history=list(h[1].header.get('HISTORY',[]))
                histories.append(dict(rxte_obsid=obs,path=str(p.relative_to(ROOT)),sha256=sha256(p),model=model,model_sha256=modelhash,history=history))
        rows.append(out)
    pd.DataFrame(rows).to_csv(validation_path(ROOT,'results/validation_heasoft/heasoft_product_audit.csv'),index=False)
    validation_path(ROOT,'results/validation_heasoft/background_model_histories.json').write_text(json.dumps(histories,indent=2))
    print(pd.DataFrame(rows).status.value_counts().to_dict());verify_primary(ROOT)

if __name__=='__main__':main()
