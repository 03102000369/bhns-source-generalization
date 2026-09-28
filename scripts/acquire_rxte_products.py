"""Resumable acquisition of actual directory-listed PCA products; no data synthesis."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re

import numpy as np
import pandas as pd

from bhns.data.acquisition import retrieve_evidence

ROOT=Path(__file__).resolve().parents[1]


def acquire(row):
    row={k:(None if pd.isna(v) else v) for k,v in row.items()}
    obs=row['rxte_obsid']; directory=ROOT/'data/raw/rxte'/obs
    directory.mkdir(parents=True,exist_ok=True)
    log=directory/'acquisition.json'
    if log.exists():
        prior=json.loads(log.read_text())
        if prior['observation']['archive_identifier']==row['archive_identifier']:return prior
        history=directory/'acquisition_attempts.jsonl'
        with history.open('a') as h:h.write(json.dumps(prior)+'\n')
    base='https://heasarc.gsfc.nasa.gov/FTP/xte/data/archive/'+row['archive_identifier']+'/stdprod/'
    listing=retrieve_evidence(base,directory,'listing',timeout=40)
    result=dict(observation=row,listing=listing,products=[])
    if listing['status']=='retrieved':
        links=set(re.findall(r'href="([^"/?]+)"',Path(listing['path']).read_text()))
        stem=obs.replace('-','')
        for kind,name in [('source',f'xp{stem}_s2.pha.gz'),('background',f'xp{stem}_b2.pha.gz'),
                          ('response',f'xp{stem}.rsp.gz'),('lightcurve',f'xp{stem}_s2a.lc.gz'),('filter',f'x{stem}.xfl.gz')]:
            if name in links:
                record=retrieve_evidence(base+name,directory,kind,timeout=40)
            else:record=dict(status='absent_from_directory',url=base+name,error='Exact expected product absent from retrieved directory listing')
            record.update(product_type=kind,filename=name,rxte_obsid=obs,source_id=row['source_id'],canonical_source=row['canonical_source'])
            result['products'].append(record)
    log.write_text(json.dumps(result,indent=2))
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--sample',action='store_true');parser.add_argument('--workers',type=int,default=4);args=parser.parse_args()
    inventory=pd.read_csv(ROOT/'data/manifests/rxte_observation_inventory.csv')
    accepted=inventory[inventory.status.eq('ACCEPTED_CANDIDATE')].drop_duplicates('rxte_obsid')
    selected=[]
    for _,group in accepted.groupby('source_id',sort=True):
        group=group.sort_values(['observation_start','rxte_obsid'])
        ranks=np.unique(np.round(np.linspace(0,len(group)-1,min(32,len(group)))).astype(int))
        part=group.iloc[ranks].copy();part['selection_method']='chronological_even_rank_cap32_v1'
        part['inspection_sample']=False
        part.loc[part.iloc[np.unique(np.round(np.linspace(0,len(part)-1,min(3,len(part)))).astype(int))].index,'inspection_sample']=True
        selected.append(part)
    selection=pd.concat(selected,ignore_index=True)
    selection.to_csv(ROOT/'data/manifests/rxte_acquisition_selection.csv',index=False)
    tasks=selection[selection.inspection_sample] if args.sample else selection
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for n,result in enumerate(pool.map(acquire,tasks.to_dict('records')),1):
            ok=sum(p['status']=='retrieved' for p in result['products'])
            print(f'{n}/{len(tasks)} {result["observation"]["rxte_obsid"]} {result["observation"]["canonical_source"]}: {ok}/5',flush=True)
    records=[]
    for p in sorted((ROOT/'data/raw/rxte').glob('*/acquisition.json')):
        r=json.loads(p.read_text());records.extend(r['products'])
        if not r['products']:
            records.append(r['listing']|dict(product_type='listing',rxte_obsid=r['observation']['rxte_obsid'],source_id=r['observation']['source_id'],canonical_source=r['observation']['canonical_source']))
    pd.DataFrame(records).to_csv(ROOT/'data/provenance/rxte_download_manifest.csv',index=False)
    print('Download manifest refreshed',flush=True)


if __name__=='__main__':main()
