"""Build canonical real-data rows and complete processing lineage from downloaded products."""
from datetime import datetime,timezone
import json
from pathlib import Path
import platform

import astropy
import numpy as np
import pandas as pd
import yaml

from bhns.data.rxte_products import process_products,sha256

ROOT=Path(__file__).resolve().parents[1]


def main():
    if (ROOT/'configs/experiment_protocol_frozen.yaml').exists():
        raise SystemExit('Frozen primary cohort is immutable. Use check_foundation.py to verify it; create a separately versioned cohort for a new reduction.')
    config_path=ROOT/'configs/reconstruction.yaml';config=yaml.safe_load(config_path.read_text())
    roster=pd.read_csv(ROOT/'data/reference/reference_source_roster.csv').drop_duplicates('source_id').set_index('source_id')
    inventory=pd.read_csv(ROOT/'data/manifests/rxte_observation_inventory.csv')
    accepted=set(inventory.loc[inventory.status.eq('ACCEPTED_CANDIDATE'),'rxte_obsid'])
    output=ROOT/'data/processed';(output/'native').mkdir(parents=True,exist_ok=True)
    provenance=ROOT/'data/provenance/rxte_processing';provenance.mkdir(parents=True,exist_ok=True)
    rows=[];excluded=[];grids=[];summaries=[]
    for log in sorted((ROOT/'data/raw/rxte').glob('*/acquisition.json')):
        record=json.loads(log.read_text());o=record['observation'];obs=o['rxte_obsid']
        try:
            if obs not in accepted:raise ValueError('Not an accepted archive candidate')
            target=roster.loc[o['source_id']]
            if target.classification_status!='VERIFIED' or target.class_label!=o['class_label']:raise ValueError('Unverified or conflicting class label')
            meta,arrays=process_products(record['products'],o,target.aliases.split('|'))
            npz=output/'native'/f'{obs}.npz';np.savez_compressed(npz,**arrays)
            process=dict(provenance_id=obs,source_id=o['source_id'],canonical_source=o['canonical_source'],class_label=o['class_label'],
                         classification_reference=target.classification_reference,acquisition_record=str(log.relative_to(ROOT)),
                         acquisition_sha256=sha256(log),config_path=str(config_path.relative_to(ROOT)),config_sha256=sha256(config_path),
                         processing_code_sha256=sha256(ROOT/'src/bhns/data/rxte_products.py'),
                         software=dict(python=platform.python_version(),numpy=np.__version__,astropy=astropy.__version__),
                         processed_at=datetime.now(timezone.utc).isoformat(),output_path=str(npz.relative_to(ROOT)),output_sha256=sha256(npz),
                         inputs=record['products'],metadata=meta)
            pp=provenance/f'{obs}.json';pp.write_text(json.dumps(process,indent=2,allow_nan=False))
            quality=meta['net_count_rate']>config['quality_cut']['minimum_net_rate']
            row=dict(observation_id=obs,rxte_obsid=obs,source_id=o['source_id'],canonical_source=o['canonical_source'],raw_source_name=meta['object'],
                     class_label=o['class_label'],observation_time=meta['date_obs'],exposure=meta['exposure'],
                     source_count_rate=meta['source_count_rate'],background_count_rate=meta['background_count_rate'],net_count_rate=meta['net_count_rate'],
                     passes_quality_cut=quality,usable=quality,exclusion_reason='' if quality else 'net_5_25_keV_recorded_rate_not_greater_than_5_count_s_PCU',
                     errors_available=meta['errors_available'],provenance_id=obs,provenance_path=str(pp.relative_to(ROOT)),
                     provenance_sha256=sha256(pp),representation=meta['representation'],pcus='|'.join(map(str,meta['pcus'])),
                     deadtime_status=meta['deadtime_status'],grid_id=meta['grid_id'])
            row.update({f'spectrum_{i:02d}':float(v) for i,v in enumerate(arrays['spectrum'])})
            if meta['errors_available']:row.update({f'error_{i:02d}':float(v) for i,v in enumerate(arrays['error'])})
            rows.append(row);summaries.append(meta|dict(source=o['canonical_source'],class_label=o['class_label']))
            grids.append(dict(rxte_obsid=obs,native_channels_used=meta['native_channels_used'],minimum_keV=meta['native_min_keV'],maximum_keV=meta['native_max_keV'],
                              native_grid_id=meta['grid_id'],native_array_path=str(npz.relative_to(ROOT)),gain_epoch='response_specific_EBOUNDS',
                              calibration_identifier=meta['response_metadata']['calibration_identifier'],response_identifier=next(p['filename'] for p in record['products'] if p['product_type']=='response'),
                              transformation=meta['representation'],output_bins=43,output_minimum_keV=5.,output_maximum_keV=25.))
        except (ValueError,KeyError,OSError,IndexError) as exc:
            excluded.append(dict(rxte_obsid=obs,source_id=o['source_id'],canonical_source=o['canonical_source'],stage='processing',exclusion_reason=str(exc)))
    frame=pd.DataFrame(rows)
    if len(frame):
        counts=frame[frame.usable].groupby('source_id').size()
        small=set(counts[counts<config['minimum_usable_observations_per_source']].index)
        mask=frame.usable & frame.source_id.isin(small)
        frame.loc[mask,'usable']=False;frame.loc[mask,'exclusion_reason']='fewer_than_4_quality_passing_observations_for_source'
        for row in frame[~frame.usable].to_dict('records'):
            excluded.append({k:row[k] for k in ['rxte_obsid','source_id','canonical_source','exclusion_reason']}|dict(stage='quality_or_source_sufficiency'))
    frame.to_csv(output/'observations.csv',index=False)
    pd.DataFrame(grids).to_csv(output/'energy_grid_metadata.csv',index=False)
    pd.DataFrame(excluded,columns=['rxte_obsid','source_id','canonical_source','stage','exclusion_reason']).to_csv(ROOT/'data/manifests/excluded_observations.csv',index=False)
    (ROOT/'data/provenance/reconstruction/product_inspection.json').write_text(json.dumps(summaries,indent=2,allow_nan=False))
    # Preserve all failures and reference rows, even when no physical source was resolved.
    comparison=[]
    full_roster=pd.read_csv(ROOT/'data/reference/reference_source_roster.csv').fillna('')
    for r in full_roster.to_dict('records'):
        sid=r['source_id'];cand=inventory[inventory.source_id.eq(sid)]
        processed=frame[frame.source_id.eq(sid)] if len(frame) else frame
        logs=[p for p in (ROOT/'data/raw/rxte').glob('*/acquisition.json') if json.loads(p.read_text())['observation']['source_id']==sid] if sid else []
        downloaded=sum(all(any(x['product_type']==kind and x['status']=='retrieved' for x in json.loads(p.read_text())['products']) for kind in ['source','background','response']) for p in logs)
        comparison.append(dict(reference_source=r['reference_source_name'],canonical_source=r['canonical_source_name'],reference_count=r['reference_observation_count'],
                               reference_class=r['reference_class'],adopted_class=r['class_label'],archive_candidates=int(cand.rxte_obsid.nunique()),
                               accepted_candidates=int(cand[cand.status.eq('ACCEPTED_CANDIDATE')].rxte_obsid.nunique()),
                               downloaded=downloaded,processed=len(processed),quality_pass=int(processed.passes_quality_cut.sum()) if len(processed) else 0,
                               usable=int(processed.usable.sum()) if len(processed) else 0,notes=r['notes']))
    comp=pd.DataFrame(comparison);comp.to_csv(ROOT/'results/reference_dataset_comparison.csv',index=False)
    head='# Reference dataset comparison\n\nReference: 61 published rows, 14,885 reported observations. Counts are never forced to match. This bounded reconstruction caps chronological ranks at 32 per physical source; the two V4641/SAX designations refer to one system and their reconstructed counts must not be added. Archive candidates include ambiguous and unobserved proposal records; accepted candidates require archived full ObsIDs and reviewed name/position.\n\n'
    columns=['reference_source','canonical_source','reference_count','archive_candidates','accepted_candidates','downloaded','processed','quality_pass','usable']
    table='| '+' | '.join(columns)+' |\n|'+ '|'.join(['---']*len(columns))+'|\n'
    table+='\n'.join('| '+' | '.join(str(r[c]) for c in columns)+' |' for r in comparison)
    (ROOT/'reports/reference_dataset_comparison.md').write_text(head+table+'\n\nSource exclusions and citations are retained in the machine-readable comparison and full roster. All processing/quality failures are in excluded_observations.csv.\n')
    print(json.dumps(dict(processed=len(frame),usable=int(frame.usable.sum()) if len(frame) else 0,rejected=len(excluded)),indent=2))


if __name__=='__main__':main()
