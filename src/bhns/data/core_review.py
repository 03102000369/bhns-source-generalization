"""Real-cohort gate review, separate from legacy author-array intake."""
import json
from pathlib import Path

from bhns.data.core_gate import load_core_frame,validate_core
from bhns.data.real_data_review import inspect_real_structure
from bhns.data.rxte_products import sha256
from bhns.reproducibility import run_record,write_json


def run_core_review(root,config,software_pass):
    root=Path(root);gate=validate_core(root)
    record=run_record(config,project_root=root,experiment_name='core-real-data-review')
    record.update(status='BLOCKED',gate1a_status=gate['status'],problems=[],checks=None,models_trained=0)
    if not software_pass:record.update(status='FAIL',problems=['Environment/software tests did not pass'])
    elif gate['status']!='PASS':record['problems']=gate['problems']
    else:
        try:
            frame=load_core_frame(root)
            record['checks']=inspect_real_structure(frame,config)
            pca_config={**config,'preprocessing':{**config['preprocessing'],'pca_components':5}}
            record['PCA_training_only_checks']=inspect_real_structure(frame,pca_config)
            record.update(status='PASS',dataset_sha256=sha256(root/'data/processed/observations.csv'))
        except (ValueError,KeyError,OSError) as exc:record.update(status='FAIL',problems=[str(exc)])
    write_json(root/'reports/gates_0_2_real_data_review.json',record)
    (root/'reports/gates_0_2_real_data_review.md').write_text(
        '# Gates 0–2 on real data\n\nStatus: **'+record['status']+'**. Gate 1A: '+gate['status']+'.\n\n'
        +'\n'.join('- '+x for x in record['problems'])
        +'\n\nThe real-data audit exercises existing observation/grouped/LOSO folds, source-disjoint inner validation, equal-source weights and source-label permutation integrity. '
        'It fits fresh scaling pipelines and repeats with PCA on training rows only. Actual ObsIDs and physical sources are stored for every partition. '
        'Observation-wise outer source overlap is intentional; grouped/LOSO outer test sources never enter inner training or validation. '
        'No learned feature selection or early stopping is used by the modest primary models. Hyperparameter selection and prediction attribution are checked again by the experiment runner. '
        'A software PASS alone is not a scientific admission decision.\n')
    return gate,record
