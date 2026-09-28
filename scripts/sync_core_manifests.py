"""Refresh the existing census/alias/manifests from the admitted core cohort."""
import json
from pathlib import Path
import pandas as pd
from bhns.data.aliases import AliasResolver,validate_registry
from bhns.data.core_gate import load_core_frame
from bhns.data.source_manifest import build_source_manifest,validate_manifest

ROOT=Path(__file__).resolve().parents[1]


def main():
    roster=pd.read_csv(ROOT/'data/reference/reference_source_roster.csv').fillna('')
    verified=roster[roster.classification_status.eq('VERIFIED')].drop_duplicates('source_id')
    frame=load_core_frame(ROOT);observations=pd.read_csv(ROOT/'data/processed/observations.csv')
    evidence=[]
    for r in verified[verified.source_id.isin(frame.source_id)].itertuples():
        evidence.append(dict(source_id=r.source_id,source_name=r.canonical_source_name,compact_object_class=r.class_label,
                             label_reference=r.classification_reference,label_status='verified',notes=r.notes))
    evidence=pd.DataFrame(evidence);census=build_source_manifest(frame,evidence);validate_manifest(frame,census)
    evidence.to_csv(ROOT/'data/manifests/label_provenance.csv',index=False);census.to_csv(ROOT/'data/manifests/source_manifest.csv',index=False)
    registry=pd.read_csv(ROOT/'data/manifests/source_registry.csv').fillna('').set_index('source_id')
    for r in verified.itertuples():
        if r.source_id not in registry.index:
            registry.loc[r.source_id]=dict(canonical_source_name=r.canonical_source_name,class_label=r.class_label,class_label_text=r.class_label,
                classification_status='verified',classification_reference=r.classification_reference,classification_evidence=r.notes,
                identity_reference=r.classification_reference,included_in_trusted_cohort=r.source_id in set(frame.source_id),
                confidence_status='independent catalog evidence; explicit archive name plus position',notes=r.notes)
        registry.loc[r.source_id,'included_in_trusted_cohort']=r.source_id in set(frame.source_id)
    registry=registry.reset_index();validate_registry(registry)
    aliases=pd.read_csv(ROOT/'data/manifests/source_aliases.csv').fillna('').to_dict('records')
    for r in verified.itertuples():
        for name in r.aliases.split('|'):
            aliases.append(dict(alias=name,source_id=r.source_id,alias_reference=r.classification_reference,status='verified',notes='Explicit reconstructed-roster designation; archive matches also require independent position.'))
    # Archive formatting variants have already passed the explicit roster plus position check.
    accepted=pd.read_csv(ROOT/'data/manifests/rxte_observation_inventory.csv').query("status == 'ACCEPTED_CANDIDATE'")
    for r in accepted[['source_id','archive_target_name','query_record']].drop_duplicates().itertuples():
        aliases.append(dict(alias=r.archive_target_name,source_id=r.source_id,alias_reference=r.query_record,status='verified',notes='Formatting-equivalent reviewed designation with catalog-coordinate agreement.'))
    aliases=pd.DataFrame(aliases).drop_duplicates(['alias','source_id'])
    resolver=AliasResolver(registry,aliases)
    for r in observations.itertuples():
        if resolver.canonicalize_source_name(r.raw_source_name).source_id!=r.source_id:raise ValueError('Legacy exact alias resolver disagrees with core mapping')
    registry.to_csv(ROOT/'data/manifests/source_registry.csv',index=False);aliases.to_csv(ROOT/'data/manifests/source_aliases.csv',index=False)
    # Flat indexes point to the complete multi-product JSON lineage, never replace it.
    manifest=observations[['observation_id','rxte_obsid','source_id','canonical_source','raw_source_name','class_label','observation_time','usable','exclusion_reason']].copy()
    manifest['instrument']='RXTE/PCA';manifest['data_product']=observations.representation
    manifest['spectrum_path_or_reference']='data/processed/native/'+observations.rxte_obsid+'.npz'
    manifest['error_path_or_reference']=manifest.spectrum_path_or_reference
    manifest['energy_grid_id']=observations.grid_id;manifest['feature_record_id']=observations.rxte_obsid;manifest['provenance_record_id']=observations.provenance_id
    failed=pd.read_csv(ROOT/'data/manifests/excluded_observations.csv').query("stage == 'processing'")
    failure_rows=[]
    for r in failed.itertuples():
        log=json.loads((ROOT/'data/raw/rxte'/r.rxte_obsid/'acquisition.json').read_text())['observation']
        failure_rows.append(dict(observation_id=r.rxte_obsid,rxte_obsid=r.rxte_obsid,source_id=r.source_id,canonical_source=r.canonical_source,
                                 raw_source_name=log['archive_target_name'],class_label=log['class_label'],usable=False,exclusion_reason=r.exclusion_reason,instrument='RXTE/PCA'))
    pd.concat([manifest,pd.DataFrame(failure_rows)],ignore_index=True).sort_values('rxte_obsid').to_csv(ROOT/'data/manifests/observation_manifest.csv',index=False)
    provenance=[]
    for r in observations.itertuples():
        p=json.loads((ROOT/r.provenance_path).read_text());source=next(x for x in p['inputs'] if x['product_type']=='source')
        provenance.append(dict(provenance_record_id=r.provenance_id,observation_id=r.observation_id,rxte_obsid=r.rxte_obsid,source_id=r.source_id,
            status='verified',original_location=source['url'],raw_path=source['path'],raw_sha256=source['sha256'],product_path=p['output_path'],product_sha256=p['output_sha256'],
            acquisition_date=source['accessed_at'],preprocessing_method=r.representation,feature_extraction_version=r.representation,
            source_mapping_reference=p['acquisition_record'],source_mapping_status='verified',flux_units=p['metadata']['units'],error_units=p['metadata']['units'],
            error_definition='Propagated archive statistical covariance; calibration/background systematics excluded',zero_error_policy='no artificial replacements',zero_error_reason='',
            energy_grid_id=r.grid_id,pm_definition_id='',processing_log_path=r.provenance_path,processing_log_sha256=r.provenance_sha256))
    pd.DataFrame(provenance).to_csv(ROOT/'data/provenance/observation_provenance.csv',index=False)
    print(f'Existing census/alias infrastructure validates {len(frame)} observations and {len(census)} physical sources')


if __name__=='__main__':main()
