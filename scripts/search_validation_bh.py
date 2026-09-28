"""Conservative new physical BH systems, using the existing exact archive query."""
from pathlib import Path
import json,re
import numpy as np
import pandas as pd
import build_rxte_inventory as old

ROOT=Path(__file__).resolve().parents[1]
old.EVIDENCE=ROOT/'data/provenance/validation_heasoft/expansion';old.EVIDENCE.mkdir(parents=True,exist_ok=True)
TARGETS=[
 dict(source_id='gro_j1655_40',canonical_source_name='GRO J1655-40',aliases='GRO J1655-40|GROJ1655-40',ra_deg=15*(16+54/60+.14/3600),dec_deg=-(39+50/60+44.9/3600),classification_reference='https://www.nature.com/articles/378157a0',position_reference='https://chandra.harvard.edu/photo/2025/j1655/index.html',notes='Secure dynamical BH; BlackCAT Table A.4 independently retains mass 6.0 +/-0.4 Msun; missing astrometry in adopted primary Table A.1 is resolved separately here.'),
 dict(source_id='grs_1915_105',canonical_source_name='GRS 1915+105',aliases='GRS 1915+105|GRS1915+105',ra_deg=15*(19+15/60+11.55/3600),dec_deg=10+56/60+44.8/3600,classification_reference='https://arxiv.org/abs/1304.1808',position_reference='https://arxiv.org/abs/1510.08869',notes='Dynamical mass from donor spectroscopy; independent position in existing CDS BlackCAT Table A.1; new validation source outside reference subset.'),
 dict(source_id='v404_cyg',canonical_source_name='V404 Cyg',aliases='V404 Cyg|V404CYG|GS2023+338|GS 2023+338',ra_deg=15*(20+24/60+3.82/3600),dec_deg=33+52/60+1.9/3600,classification_reference='https://academic.oup.com/mnras/article/394/3/1440/1069184',position_reference='https://arxiv.org/abs/1510.08869',notes='Dynamically confirmed BH, 6.08 Msun mass function; position and aliases in BlackCAT. RXTE mission preceded 2015 outburst; no assumption that quiescent spectra pass rate cut.')]

def main():
    rows=[];summaries=[]
    for target in TARGETS:
        rec=old.query_source(target);accepted=[]
        for r in rec.get('rows',[]):
            if r['time'] in ['null',''] or r['ra'] in ['null',''] or r['dec'] in ['null','']:
                rows.append(dict(rxte_obsid=r['obsid'],source_id=target['source_id'],canonical_source=target['canonical_source_name'],class_label='BH',status='UNADMITTED_MISSING_ARCHIVE_TIME_OR_POSITION'))
                continue
            sep=old.separation(float(r['ra']),float(r['dec']),target['ra_deg'],target['dec_deg'])
            exact=old.key(r['target_name']) in {old.key(a) for a in target['aliases'].split('|')}
            ok=exact and sep<=.05 and r['status']=='archived' and bool(re.fullmatch(r'\d{5}-\d{2}-\d{2}-\d{2}',r['obsid']))
            row=dict(rxte_obsid=r['obsid'],source_id=target['source_id'],canonical_source=target['canonical_source_name'],class_label='BH',observation_mjd=float(r['time']),archive_target_name=r['target_name'],ra=float(r['ra']),dec=float(r['dec']),separation_deg=sep,status='ACCEPTED_CANDIDATE' if ok else 'UNADMITTED',archive_identifier=f"AO{int(r['cycle'])}/P{str(r['prnb']).zfill(5)}/{r['obsid']}")
            rows.append(row)
            if ok:accepted.append(row)
        summaries.append({**target,'candidate_rows':len(rec.get('rows',[])),'accepted_ObsIDs':len({r['rxte_obsid'] for r in accepted})})
    f=pd.DataFrame(rows);f.to_csv(ROOT/'results/validation_heasoft/bh_expansion_inventory.csv',index=False)
    parts=[]
    from astropy.time import Time
    for sid,g in f[f.status.eq('ACCEPTED_CANDIDATE')].drop_duplicates('rxte_obsid').groupby('source_id'):
        g=g.sort_values(['observation_mjd','rxte_obsid']);g=g.iloc[np.unique(np.round(np.linspace(0,len(g)-1,min(8,len(g)))).astype(int))].copy();g['observation_time']=Time(g.observation_mjd.to_numpy(),format='mjd').isot;parts.append(g)
    pd.concat(parts).to_csv(ROOT/'data/processed/validation_heasoft/expanded_selection.csv',index=False)
    (ROOT/'results/validation_heasoft/bh_expansion_evidence.json').write_text(json.dumps(summaries,indent=2));print(summaries,flush=True)

if __name__=='__main__':main()
