"""Reconstruct the complete reference roster and query verified targets, without ML."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import io
import json
from pathlib import Path
import re
import warnings
from urllib.parse import urlencode

import numpy as np
import pandas as pd
from astropy.io import ascii

from bhns.data.acquisition import retrieve_evidence

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'data/provenance/reconstruction'


def key(name):
    """Only formatting differences; never edit digits, signs or punctuation."""
    return re.sub(r'[\s_]', '', name).upper()


def build_roster():
    ref = pd.read_csv(ROOT / 'data/provenance/published_source_roster.csv')
    catalog = EVIDENCE / 'catalog_working_copies'
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        bh = ascii.read(str(catalog / 'tablea1.dat'), readme=str(catalog / 'ReadMe'), format='cds')
    bh_rows = {key(str(r['Name'])): r for r in bh}
    ns = {key(r[0]): r for r in json.loads((EVIDENCE / 'minbar_sources_tables.json').read_text())[0][1:]}
    # Explicitly reviewed designation variants. No fuzzy name inference is used.
    variants = {'V4641SGR':'SAXJ1819.3-2525', 'GX339-4':'1H1659-487',
                '4U1543-47':'4U1543-475', '4U0614+091':'4U0614+09',
                '4U1254-690':'4U1254-69', '4U1608-52':'4U1608-522',
                '4U1636-53':'4U1636-536', '4U1746-371':'4U1746-37',
                '4U1735-44':'4U1735-444', 'AQLX1':'AQLX-1'}
    out = []
    for r in ref.to_dict('records'):
        name = r['published_source_name']; lookup = variants.get(name, name)
        row = dict(reference_source_name=name, canonical_source_name='', source_id='', aliases='',
                   reference_class=r['published_class_label'], class_label='UNRESOLVED',
                   classification_status='UNRESOLVED', classification_reference='',
                   reference_observation_count=r['published_observation_count'],
                   identity_status='UNRESOLVED', ra_deg=np.nan, dec_deg=np.nan,
                   notes='No sufficiently secure identity and classification evidence adopted in this reconstruction.')
        if lookup in bh_rows:
            b = bh_rows[lookup]
            if str(b['f_Name']) == '*' and lookup != 'XTEJ1650-500':
                canonical = 'V4641 Sgr' if lookup == 'SAXJ1819.3-2525' else ('GX 339-4' if lookup == '1H1659-487' else str(b['Name']))
                row.update(canonical_source_name=canonical, class_label='BH', classification_status='VERIFIED',
                           classification_reference='https://arxiv.org/abs/1510.08869',
                           ra_deg=15*(float(b['RAh'])+float(b['RAm'])/60+float(b['RAs'])/3600),
                           dec_deg=(1 if str(b['DE-'])=='+' else -1)*(float(b['DEd'])+float(b['DEm'])/60+float(b['DEs'])/3600),
                           notes='BlackCAT dynamical sample (Table 4); coordinates and counterpart designation from CDS Table A.1. Conservative secure-BH subset.')
                row['aliases'] = '|'.join(dict.fromkeys([name, canonical, str(b['Name'])]))
            else:
                row['notes'] = 'BlackCAT candidate or dynamical mass constraint not sufficiently decisive for this conservative primary subset.'
        if lookup in ns:
            n = ns[lookup]
            if (float(n[6] or 0)>0 or 'P' in n[1]) and name != 'GRS1747-312':
                row.update(canonical_source_name=n[0], aliases='|'.join(dict.fromkeys([name,n[0]])),
                           class_label='NS', classification_status='VERIFIED',
                           classification_reference='https://burst.sci.monash.edu/sources',
                           ra_deg=float(n[2]),dec_deg=float(n[3]),
                           notes=f'MINBAR source catalog: type {n[1]}, {n[6]} cataloged bursts. Type P independently identifies a pulsar. Explicit designation variant where listed.')
        if row['class_label'] in ('BH','NS'):
            extra = {
                'GS1354-64': ['GS_1354-644', 'X1354-644', 'BW Cir'],
                '1A1744-361': ['A1744-361', 'A1744-36', 'X1744-361'],
                'MXB1658-298': ['X1658-298'],
            }.get(name, [])
            if extra:
                row['aliases'] += '|' + '|'.join(extra)
                row['notes'] += ' Archive designation reviewed against primary literature and independent catalog position; see reconstruction/alias_evidence.csv.'
            row['source_id'] = re.sub(r'[^a-z0-9]+','_',row['canonical_source_name'].lower()).strip('_')
            row['identity_status'] = 'ALIAS_VERIFIED' if name in variants or name=='SAXJ1819.3-2525' else 'VERIFIED'
        if name in ('TERZAN5','NGC6440','GRS1747-312'):
            row.update(identity_status='AMBIGUOUS',notes='Multiple compact sources in an unresolved cluster field; object-level attribution requires observation-specific evidence.')
        if name=='XTEJ1908+094':
            row['notes']='Specific published XTE J1908+094 / 4U 1907+097 attribution conflict preserved. No bulk relabeling; BH identity alone cannot attribute the published spectra.'
        if name=='IGRJ17379-3747':
            row.update(canonical_source_name='IGR J17379-3747',source_id='igr_j17379_3747',aliases=name,
                       class_label='NS', classification_status='VERIFIED', identity_status='VERIFIED',
                       classification_reference='https://arxiv.org/abs/1807.08574v2',
                       notes='Coherent millisecond pulsations: Sanna et al. 2018 (see existing registry). Published BH label conflicts; query exact designation, but no spectra admitted without independently verified pointing.')
        if name=='IGRJ17497-2821':
            row['notes']='Published NS label conflicts with BlackCAT BH-candidate listing; excluded pending classification review.'
        out.append(row)
    result=pd.DataFrame(out); (ROOT/'data/reference').mkdir(exist_ok=True)
    result.to_csv(ROOT/'data/reference/reference_source_roster.csv',index=False)
    return result


def query_source(row):
    sid=row['source_id']; cache=EVIDENCE/f'query_{sid}.json'
    if cache.exists():return json.loads(cache.read_text())
    aliases=row['aliases'].split('|')
    names = sorted(set(aliases+[a.upper().replace(' ','_') for a in aliases]+[key(a) for a in aliases]))
    clause=' OR '.join("target_name = '"+a.replace("'","''")+"'" for a in names)
    if np.isfinite(row['ra_deg']):
        # Broad cone is discovery only. Admission later requires position AND exact designation.
        clause += f" OR CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{row['ra_deg']},{row['dec_deg']},0.3))=1"
    query='SELECT obsid,target_name,ra,dec,time,duration,exposure,status,cycle,prnb,pca_config1,pca_config2 FROM xtemaster WHERE ('+clause+') ORDER BY time,obsid'
    url='https://heasarc.gsfc.nasa.gov/xamin/vo/tap/sync?'+urlencode(dict(REQUEST='doQuery',LANG='ADQL',FORMAT='text/plain',QUERY=query,MAXREC=30000))
    record=retrieve_evidence(url,EVIDENCE/'queries',sid,timeout=60)
    record.update(source_id=sid,query=query)
    if record['status']=='retrieved':
        raw=Path(record['path']).read_text()
        lines=[l for l in raw.splitlines() if '|' in l]
        if not lines or 'Query Error' in raw or 'OVERFLOW' in raw:record.update(status='service_error',error=raw[:1000])
        else:record['rows']=[{k.strip():v.strip() for k,v in r.items()} for r in csv.DictReader(io.StringIO('\n'.join(lines)),delimiter='|')]
    cache.write_text(json.dumps(record,indent=2));return record


def separation(ra,dec,ra0,dec0):
    a,b,a0,b0=np.radians([ra,dec,ra0,dec0])
    return np.degrees(2*np.arcsin(np.sqrt(np.clip(np.sin((b-b0)/2)**2+np.cos(b)*np.cos(b0)*np.sin((a-a0)/2)**2,0,1))))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--query',action='store_true');args=parser.parse_args()
    roster=build_roster()
    if not args.query:return
    targets=roster[roster.classification_status.eq('VERIFIED')].drop_duplicates('source_id')
    records=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for target,result in zip(targets.to_dict('records'),pool.map(query_source,targets.to_dict('records'))):
            names={key(a) for a in target['aliases'].split('|')}
            for r in result.get('rows',[]):
                try:sep=separation(float(r['ra']),float(r['dec']),target['ra_deg'],target['dec_deg'])
                except ValueError:sep=np.nan
                exact=key(r['target_name']) in names
                accepted=exact and np.isfinite(sep) and sep<=0.05 and r['status']=='archived' and bool(re.fullmatch(r'\d{5}-\d{2}-\d{2}-\d{2}',r['obsid']))
                records.append(dict(rxte_obsid=r['obsid'],source_id=target['source_id'],canonical_source=target['canonical_source_name'],
                     archive_target_name=r['target_name'],reference_class=target['reference_class'],class_label=target['class_label'],
                     proposal_id=r['prnb'],cycle=r['cycle'],observation_start=r['time'],duration=r['duration'],
                     exposure=r['exposure'],archive_identifier=f"AO{r['cycle']}/P{str(r['prnb']).zfill(5)}/{r['obsid']}",
                     mapping_method='explicit_designation_and_independent_catalog_position',mapping_confidence='high' if accepted else 'unresolved',
                     separation_deg=sep,ra=r['ra'],dec=r['dec'],archive_status=r['status'],status='ACCEPTED_CANDIDATE' if accepted else 'AMBIGUOUS_OR_UNAVAILABLE',
                     query_record=str(EVIDENCE/f"query_{target['source_id']}.json"),
                     notes='' if accepted else f'exact_name={exact}; position_within_3_arcmin={bool(sep<=.05)}; archived={r["status"]}; full_ObsID={r["obsid"]}'))
            print(target['canonical_source_name'],result['status'],len(result.get('rows',[])),flush=True)
    frame=pd.DataFrame(records)
    if len(frame):
        frame=frame.drop_duplicates(['source_id','rxte_obsid','archive_target_name'])
        conflicts=frame[frame.status.eq('ACCEPTED_CANDIDATE')].groupby('rxte_obsid').source_id.nunique()
        frame.loc[frame.rxte_obsid.isin(conflicts[conflicts>1].index),'status']='AMBIGUOUS_MULTIPLE_SOURCES'
    frame.to_csv(ROOT/'data/manifests/rxte_observation_inventory.csv',index=False)
    print('TARGETS',len(targets),'ROWS',len(frame),'ACCEPTED',sum(frame.status.eq('ACCEPTED_CANDIDATE')),flush=True)


if __name__=='__main__':main()
