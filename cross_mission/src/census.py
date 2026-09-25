"""Catalogue discovery; no learned spectral quantities or prediction access."""
import csv
import io
import json
import re
import warnings
from html.parser import HTMLParser
import numpy as np
import pandas as pd
from astropy.io import ascii
from astropy.time import Time
from evidence import ROOT, sha256

def key(name):
    return re.sub(r'[\s_]', '', str(name)).upper()

class Tables(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows=[]; self.row=[]; self.cell=None; self.link=''
    def handle_starttag(self, tag, attrs):
        if tag=='tr': self.row=[]
        if tag in ('td','th'): self.cell=''
        if tag=='a' and self.cell is not None and not self.row:
            self.link=dict(attrs).get('href','')
    def handle_data(self, data):
        if self.cell is not None:self.cell+=data
    def handle_endtag(self, tag):
        if tag in ('td','th') and self.cell is not None:
            self.row.append(self.cell.strip()); self.cell=None
        if tag=='tr' and len(self.row)==9:
            self.rows.append((self.row,self.link));self.link=''

def separation(ra, dec, ra0, dec0):
    a,b,a0,b0=np.radians([ra,dec,ra0,dec0])
    return np.degrees(2*np.arcsin(np.sqrt(np.clip(np.sin((b-b0)/2)**2+np.cos(b)*np.cos(b0)*np.sin((a-a0)/2)**2,0,1))))

def archive():
    path=ROOT/'data/reference/evidence/numaster_all.txt'
    meta=json.loads(path.with_name(path.name+'.retrieval.json').read_text())
    assert sha256(path)==meta['sha256']
    raw=path.read_text()
    assert 'OVERFLOW' not in raw and 'Query Error' not in raw
    lines=[line for line in raw.splitlines() if '|' in line]
    rows=[{k.strip():v.strip() for k,v in row.items()} for row in csv.DictReader(io.StringIO('\n'.join(lines)),delimiter='|')]
    return pd.DataFrame(rows)

def main():
    parent=ROOT.parent
    phase=pd.read_csv(parent/'data/filter_sensitivity/secure_source_universe.csv').fillna('')
    members=set(pd.read_csv(parent/'data/processed/validation_heasoft/expanded_source_observations.csv').source_id)
    registry={}
    for r in phase.to_dict('records'):
        registry[key(r['canonical_source'])]=dict(canonical_source=r['canonical_source'],source_id=r['source_id'],aliases=r['aliases'],class_label=r['class_label'],classification_evidence=r['notes'],classification_reference=r['classification_reference'],ra_deg=r['ra_deg'],dec_deg=r['dec_deg'],coordinate_reference=r['classification_reference'],secure_label=True,field_review_required=False,notes='Inherited secure evidence; NuSTAR identity independently audited.')
    cat=parent/'data/provenance/reconstruction/catalog_working_copies'
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        # CDS byte ranges from the retained ReadMe; unused numeric sentinel
        # columns (e.g. '---' in vrot) need not be coerced to numbers.
        dyn=[{name:line[start:end].strip() for name,start,end in [('Name',0,18),('Ctp',21,31),('l_M1',86,88),('M1',88,93),('Ref',164,252)]} for line in (cat/'tablea4.dat').read_text().splitlines() if line.strip()]
        pos=ascii.read(str(cat/'tablea1.dat'),readme=str(cat/'ReadMe'),format='cds')
    positions={key(r['Name']):r for r in pos}
    known={key(a) for r in registry.values() for a in r['aliases'].split('|')}
    for r in dyn:
        name=str(r['Name']);k=key(name)
        if k in known:continue
        lookup='A0620-003' if k=='3A0620-003' else k
        if lookup not in positions:continue
        p=positions[lookup]
        secure=k not in {'XTEJ1650-500','GROJ0422+32','SWIFTJ1357.2-0933'}
        registry[k]=dict(canonical_source=name,source_id=re.sub('[^a-z0-9]+','_',name.lower()).strip('_'),aliases='|'.join(dict.fromkeys([name,str(p['Name']),str(r['Ctp']) if not np.ma.is_masked(r['Ctp']) else name])),class_label='BH' if secure else 'UNRESOLVED',classification_evidence=f'BlackCAT Table A.4 dynamical evidence; M1={r["l_M1"]} {r["M1"]} Msun; references {r["Ref"]}. '+('Conservative dynamical inclusion.' if secure else 'Not counted: adopted evidence has a weak mass bound or lacks donor-star detection; needs primary follow-up.'),classification_reference='https://arxiv.org/abs/1510.08869',ra_deg=15*(float(p['RAh'])+float(p['RAm'])/60+float(p['RAs'])/3600),dec_deg=(1 if str(p['DE-'])=='+' else -1)*(float(p['DEd'])+float(p['DEm'])/60+float(p['DEs'])/3600),coordinate_reference='CDS J/A+A/587/A61 Table A.1',secure_label=secure,field_review_required=False,notes='Broader dynamical-catalogue discovery outside the Phase-I roster.')
    parser=Tables();parser.feed((ROOT/'data/reference/evidence/minbar_sources.html').read_text())
    for n,ref in parser.rows:
        if n[0]=='NAME':continue
        k=key(n[0]);secure=float(n[6] or 0)>0 or 'P' in n[1]
        if k in registry:continue
        registry[k]=dict(canonical_source=n[0],source_id=re.sub('[^a-z0-9]+','_',n[0].lower()).strip('_'),aliases=n[0],class_label='NS' if secure else 'UNRESOLVED',classification_evidence=f'MINBAR direct evidence: {n[6]} catalogue bursts; type={n[1]}; P denotes pulsar. '+('Secure neutron-star evidence.' if secure else 'No positive burst count or pulsar flag adopted; not in secure census.'),classification_reference='https://burst.sci.monash.edu/sources'+(' | '+ref.replace('http://adsabs.harvard.edu/abs/','https://ui.adsabs.harvard.edu/abs/') if ref else ''),ra_deg=float(n[2]),dec_deg=float(n[3]),coordinate_reference='https://burst.sci.monash.edu/sources',secure_label=secure,field_review_required='G' in n[1],notes='MINBAR discovery; cluster-marked fields require object-level contamination audit.' if 'G' in n[1] else 'Broader MINBAR census outside Phase I.')
    ast=pd.read_csv(ROOT/'data/reference/evidence/new_bh_astrometry.csv')
    extra=[('Cyg X-1','X Cyg X-1','Cyg X-1|Cyg X1|Cygnus X-1|HD 226868','2102.09091','Dynamical mass 21.2 +/- 2.2 Msun (Miller-Jones et al. 2021).'),('LMC X-1','X LMC X-1','LMC X-1|LMC X1','0810.3447','Dynamical mass 10.91 +/- 1.41 Msun (Orosz et al. 2009).'),('LMC X-3','X LMC X-3','LMC X-3|LMC X3','1402.0085','Dynamical mass 6.98 +/- 0.56 Msun (Orosz et al. 2014).'),('MAXI J1820+070','MAXI J1820+070','MAXI J1820+070|ASASSN-18ey','1907.00938','Donor radial-velocity mass function 5.18 +/- 0.15 Msun (Torres et al. 2019).')]
    for name,ident,aliases,arxiv,evidence in extra:
        row=ast.loc[ast.id.eq(ident)].iloc[0]
        registry[key(name)]=dict(canonical_source=name,source_id=re.sub('[^a-z0-9]+','_',name.lower()).strip('_'),aliases=aliases,class_label='BH',classification_evidence=evidence,classification_reference='https://arxiv.org/abs/'+arxiv,ra_deg=row.ra,dec_deg=row.dec,coordinate_reference='SIMBAD TAP identity/astrometry snapshot new_bh_astrometry.csv',secure_label=True,field_review_required=False,notes='Primary dynamical paper verified independently of NuSTAR spectra; source beyond Phase I.')
    # All aliases resolve uniquely; intentional formatting changes only.
    # SIMBAD resolves both IGR catalogue designations to XTE J1737-376.
    # Keep the established Phase-I canonical ID and never count this twice.
    identities=pd.read_csv(ROOT/'data/reference/evidence/ambiguous_catalog_names.csv')
    igr=identities[identities.id.isin(['IGR J17379-3747','IGR J17380-3749'])]
    if len(igr)!=2 or igr.main_id.nunique()!=1:raise ValueError('IGR alias reconciliation evidence changed')
    old=registry.pop(key('IGR J17380-3749'))
    canonical=registry[key('IGR J17379-3747')]
    canonical['aliases']+='|'+old['aliases']+'|XTE J1737-376|IGR_J17379m3747'
    canonical.update(ra_deg=float(igr.iloc[0].ra),dec_deg=float(igr.iloc[0].dec),coordinate_reference='SIMBAD ambiguous_catalog_names.csv; both IGR aliases resolve to XTE J1737-376')
    canonical['notes']+=' IGR J17380-3749 is the same physical system, merged before splitting.'
    for alias in pd.read_csv(ROOT/'data/reference/reviewed_archive_aliases.csv').to_dict('records'):
        registry[key(alias['canonical_source'])]['aliases']+='|'+alias['archive_alias']
    amap={}
    for r in registry.values():
        r['aliases']='|'.join(a for a in r['aliases'].split('|') if a.strip())
        for a in r['aliases'].split('|'):
            if key(a) in amap and amap[key(a)]!=r['source_id']:raise ValueError('Alias conflict '+a)
            amap[key(a)]=r['source_id']
    master=archive();now=Time('2026-09-23T00:00:00').mjd
    master_rows=master.to_dict('records')
    records=[]
    for r in registry.values():
        aliases={key(a) for a in r['aliases'].split('|')}
        matched=[];public=[]
        for o in master_rows:
            exact=key(o['name']) in aliases
            try:sep=separation(float(o['ra']),float(o['dec']),float(r['ra_deg']),float(r['dec_deg']))
            except (ValueError,TypeError):sep=np.nan
            if not exact and not sep<=0.15:continue
            reason=[]
            if not exact:reason.append('NAME_REVIEW_REQUIRED')
            if not np.isfinite(sep) or sep>0.05:reason.append('POSITION_REVIEW_REQUIRED')
            if not r['secure_label']:reason.append('LABEL_UNRESOLVED')
            if r['field_review_required']:reason.append('CLUSTER_ATTRIBUTION_REVIEW')
            ispublic=o['status']=='archived' and o['public_date'] not in ('null','') and float(o['public_date'])<=now
            if not ispublic:reason.append('NOT_PUBLIC_ARCHIVED')
            science=o['observation_mode']=='SCIENCE' and re.fullmatch(r'\d{11}',o['obsid'])
            if not science:reason.append('NOT_SCIENCE_OBSERVATION')
            a=float(o['exposure_a'])>0;b=float(o['exposure_b'])>0
            if not (a and b):reason.append('NONPOSITIVE_MODULE_EXPOSURE')
            accepted=not reason
            if exact and sep<=0.05:matched.append(o['obsid'])
            if accepted:public.append(o['obsid'])
            time=float(o['time']) if o['time'] not in ('null','') else 0
            records.append(dict(obsid=o['obsid'],canonical_source=r['canonical_source'],class_label=r['class_label'],start_time=Time(time,format='mjd').isot if time>50000 else '',exposure=min(float(o['exposure_a']),float(o['exposure_b'])),target_name=o['name'],FPMA_available='CATALOG_POSITIVE_EXPOSURE' if a else 'NO_POSITIVE_EXPOSURE',FPMB_available='CATALOG_POSITIVE_EXPOSURE' if b else 'NO_POSITIVE_EXPOSURE',archive_status='PUBLIC_ARCHIVED' if ispublic else o['status'],download_status='NOT_DOWNLOADED',processing_status='NOT_ATTEMPTED',exclusion_reason=';'.join(reason),source_id=r['source_id'],exposure_a=o['exposure_a'],exposure_b=o['exposure_b'],public_date_mjd=o['public_date'],pointing_separation_arcmin=sep*60,identity_status='VERIFIED_NAME_POSITION' if exact and sep<=0.05 else 'REVIEW_REQUIRED',census_candidate=accepted,issue_flag=o['issue_flag'],comments=o['comments'],solar_activity=o['solar_activity'],data_gap=o['data_gap'],nupsdout=o['nupsdout']))
        r.update(nustar_obsids='|'.join(public),rxte_available='VERIFIED_PHASE1_PRODUCTS' if r['source_id'] in members else ('VERIFIED_ARCHIVE_INVENTORY' if r['source_id'] in set(phase.source_id)-{'igr_j17379_3747'} else 'NOT_AUDITED'),current_phase1_membership=r['source_id'] in members,identity_status='VERIFIED_NAME_POSITION' if public else ('MATCHED_NOT_ELIGIBLE' if matched else 'NO_VERIFIED_PUBLIC_POINTING'),usable_status='PUBLIC_CANDIDATE_REDUCTION_REQUIRED' if public else 'NOT_IN_INITIAL_PROCESSING_CENSUS',public_candidate_observations=len(public))
    out=pd.DataFrame(registry.values()).sort_values(['class_label','canonical_source'])
    first=['canonical_source','aliases','class_label','classification_evidence','classification_reference','nustar_obsids','rxte_available','current_phase1_membership','identity_status','usable_status','notes']
    out[first+[c for c in out if c not in first]].to_csv(ROOT/'data/reference/nustar_source_registry.csv',index=False)
    inv=pd.DataFrame(records).sort_values(['canonical_source','obsid'])
    cycles=master.set_index('obsid')['cycle'].to_dict()
    inv['archive_cycle']=inv.obsid.map(cycles).astype(int)
    inv['archive_url']=[f'https://heasarc.gsfc.nasa.gov/FTP/nustar/data/obs/{cycle:02d}/{obsid[0]}/{obsid}/' for cycle,obsid in zip(inv.archive_cycle,inv.obsid)]
    ok=inv[inv.census_candidate]
    assert ok.groupby('obsid').source_id.nunique().max()==1
    inv.to_csv(ROOT/'data/manifests/nustar_inventory.csv',index=False)
    summary=dict(archive_rows=len(master),discovery_sources=len(out),secure_label_sources=out[out.secure_label].groupby('class_label').size().to_dict(),public_candidate_sources=ok.groupby('class_label').source_id.nunique().to_dict(),candidate_observations=len(ok),new_public_sources=out[out.public_candidate_observations.gt(0)&~out.current_phase1_membership].groupby('class_label').size().to_dict())
    (ROOT/'results/census_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
    print(out[out.public_candidate_observations.gt(0)][['canonical_source','class_label','public_candidate_observations']].to_string(index=False))

if __name__=='__main__':main()
