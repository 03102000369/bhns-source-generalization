"""Gate 1A: independently reconstructed spectra. Gate 1B remains optional."""
import json
from pathlib import Path
import re

import numpy as np
import pandas as pd
import yaml

from bhns.data.rxte_products import ENERGY_EDGES,REPRESENTATION,sha256
from bhns.data.validation import validate_dataset


def load_core_frame(root,representation='SM'):
    f=pd.read_csv(Path(root)/'data/processed/observations.csv')
    f=f[f.usable.eq(True)].reset_index(drop=True)
    out=pd.DataFrame(dict(source_id=f.source_id,source_name=f.canonical_source,compact_object_class=f.class_label,obs_id=f.rxte_obsid,
                          net_count_rate=f.net_count_rate,observation_time=f.observation_time))
    for i in range(43):out[f'flux_{i:02d}']=f[f'spectrum_{i:02d}']
    if representation=='SEM' or (len(f) and f.errors_available.all()):
        if not f.errors_available.all():raise ValueError('SEM requires the same eligible cohort to have verified errors')
        errors=pd.DataFrame({f'err_{i:02d}':f[f'error_{i:02d}'] for i in range(43)})
        out=pd.concat([out,errors],axis=1)
    validate_dataset(out,representation=representation)
    return out


def validate_core(root):
    root=Path(root);problems=[];summary={}
    try:
        config_path=root/'configs/reconstruction.yaml';config=yaml.safe_load(config_path.read_text())
        f=pd.read_csv(root/'data/processed/observations.csv')
        roster=pd.read_csv(root/'data/reference/reference_source_roster.csv')
        targets=roster[roster.classification_status.eq('VERIFIED')].drop_duplicates('source_id').set_index('source_id')
        inventory=pd.read_csv(root/'data/manifests/rxte_observation_inventory.csv')
        accepted=inventory[inventory.status.eq('ACCEPTED_CANDIDATE')].drop_duplicates('rxte_obsid').set_index('rxte_obsid')
        if not len(f):raise ValueError('No real reconstructed spectra')
        if f.rxte_obsid.duplicated().any() or not f.observation_id.equals(f.rxte_obsid):raise ValueError('Duplicate or inconsistent ObsIDs')
        if not f.rxte_obsid.map(lambda x:bool(re.fullmatch(r'\d{5}-\d{2}-\d{2}-\d{2}',x))).all():raise ValueError('Invalid ObsID syntax')
        if set(c for c in f if c.startswith('spectrum_'))!={f'spectrum_{i:02d}' for i in range(43)}:raise ValueError('Invalid spectrum dimensions')
        for r in f.to_dict('records'):
            obs=r['rxte_obsid'];sid=r['source_id'];target=targets.loc[sid]
            if r['class_label']!=target.class_label or r['canonical_source']!=target.canonical_source_name:raise ValueError(f'{obs}: source/label mismatch')
            if accepted.loc[obs,'source_id']!=sid:raise ValueError(f'{obs}: uncertain archive mapping')
            pp=root/r['provenance_path']
            if sha256(pp)!=r['provenance_sha256']:raise ValueError(f'{obs}: provenance checksum mismatch')
            p=json.loads(pp.read_text())
            if p['provenance_id']!=obs or p['source_id']!=sid or p['class_label']!=r['class_label']:raise ValueError(f'{obs}: provenance identity mismatch')
            if p['config_sha256']!=sha256(config_path):raise ValueError('Processing config changed; rebuild cohort')
            if p['processing_code_sha256']!=sha256(root/'src/bhns/data/rxte_products.py'):raise ValueError('Processing code changed; rebuild cohort')
            if p['acquisition_sha256']!=sha256(root/p['acquisition_record']):raise ValueError(f'{obs}: acquisition lineage changed')
            if bool(r['errors_available'])!=bool(p['metadata']['errors_available']):raise ValueError('Error availability differs from extraction')
            for column in ['source_count_rate','background_count_rate','net_count_rate','exposure']:
                if not np.isclose(r[column],p['metadata'][column],rtol=1e-12,atol=1e-12):raise ValueError('Row metadata differs from extraction')
            if r['raw_source_name']!=p['metadata']['object'] or r['observation_time']!=p['metadata']['date_obs']:raise ValueError('Row identity/time differs from extraction')
            for product in p['inputs']:
                if product['status']=='retrieved' and sha256(product['path'])!=product['sha256']:raise ValueError(f'{obs}: raw checksum mismatch')
            if sha256(root/p['output_path'])!=p['output_sha256']:raise ValueError(f'{obs}: native output checksum mismatch')
            vector=np.array([r[f'spectrum_{i:02d}'] for i in range(43)])
            if not np.isfinite(vector).all() or not np.any(vector):raise ValueError(f'{obs}: nonfinite or all-zero spectrum')
            with np.load(root/p['output_path'],allow_pickle=False) as a:
                if not np.array_equal(a['energy_edges_keV'],ENERGY_EDGES) or not np.allclose(vector,a['spectrum'],rtol=1e-12,atol=1e-12):raise ValueError(f'{obs}: output vector/grid mismatch')
                if bool(r['errors_available']):
                    errors=np.array([r[f'error_{i:02d}'] for i in range(43)])
                    if not np.isfinite(errors).all() or np.any(errors<0) or not np.allclose(errors,a['error'],rtol=1e-12,atol=1e-12):raise ValueError(f'{obs}: invalid statistical errors')
                    if not np.allclose(errors**2,np.diag(a['covariance'])):raise ValueError('Error/covariance mismatch')
            if r['representation']!=REPRESENTATION or not np.isclose(vector.sum(),r['net_count_rate']):raise ValueError('Count-rate representation mismatch')
            if bool(r['passes_quality_cut']) != bool(r['net_count_rate']>config['quality_cut']['minimum_net_rate']):raise ValueError('Quality decision mismatch')
            if bool(r['usable']) and not bool(r['passes_quality_cut']):raise ValueError('Quality-rejected observation marked usable')
        usable=f[f.usable.eq(True)];census=usable[['source_id','class_label']].drop_duplicates()
        summary=dict(processed_observations=len(f),observations=len(usable),unique_sources=len(census),
                     BH_sources=int(census.class_label.eq('BH').sum()),NS_sources=int(census.class_label.eq('NS').sum()),
                     BH_observations=int(usable.class_label.eq('BH').sum()),NS_observations=int(usable.class_label.eq('NS').sum()),
                     observations_with_uncertainties=int(usable.errors_available.sum()),observations_without_uncertainties=int((~usable.errors_available).sum()),
                     excluded_reference_rows=int((~roster.source_id.isin(census.source_id)).sum()),
                     unresolved_identity_rows=int(roster.identity_status.isin(['UNRESOLVED','AMBIGUOUS']).sum()),
                     excluded_observations=len(pd.read_csv(root/'data/manifests/excluded_observations.csv')),
                     native_grid_count=int(usable.grid_id.nunique()),spectral_grid_status='43 fixed detector-space energy bins; native grids and covariance retained',
                     provenance_completeness='All reconstructed rows verified against checksummed raw inputs and processing outputs')
        for label in ['BH','NS']:
            if summary[f'{label}_sources']<config['minimum_sources_per_class']:problems.append(f"Only {summary[f'{label}_sources']} {label} sources; require at least {config['minimum_sources_per_class']} for the predeclared 5-fold design")
        if len(usable) and usable.groupby('source_id').size().min()<config['minimum_usable_observations_per_source']:problems.append('Admitted source has too few observations')
        if not problems:load_core_frame(root)
    except (OSError,ValueError,KeyError,IndexError) as exc:problems.append(str(exc))
    record=dict(status='BLOCKED' if problems else 'PASS',gate='1A',summary=summary,problems=problems,
                gate1b=dict(status='UNAVAILABLE_OPTIONAL',required_for_primary=False,reason='No verified PM fits supplied or generated'),
                scope='Reconstructed public standard-product detector-space cohort; not exact author-data replication',
                limitations=['Recorded rates are not deadtime-corrected or unfolded photon flux.',
                             'Response EBOUNDS handles energy assignment; response and gain-dependent detection efficiency remain possible confounders.',
                             'Archive STAT_ERR propagation omits calibration/background-model systematics.',
                             'Three-arcminute pointing/name validation does not establish imaging deblending in every field.'])
    (root/'reports/gate1a_data_report.json').write_text(json.dumps(record,indent=2))
    lines=['# Gate 1A — core spectral dataset','',f"Status: **{record['status']}**.",'',record['scope'],'']
    lines += [f'- {k}: {v}' for k,v in summary.items()]+['']+[f'- BLOCKER: {p}' for p in problems]
    lines += ['','Gate 1B: **UNAVAILABLE_OPTIONAL**; it does not block Gate 1A.','','## Scientific scope and limitations','']+[f'- {s}' for s in record['limitations']]
    (root/'reports/gate1a_data_report.md').write_text('\n'.join(lines)+'\n')
    return record
