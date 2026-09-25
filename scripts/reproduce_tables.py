"""Rebuild the main comparison table from frozen values without fitting/resampling."""
import csv,json
import pandas as pd
from verify_release import verify,ROOT
from release_support import sha256

def main():
    verify();out=ROOT/'build/reproduced/tables';out.mkdir(parents=True,exist_ok=True)
    paths=['results/primary_performance.csv','results/validation_heasoft/tables/validation_table_2_performance.csv','results/validation_heasoft/tables/validation_table_1_cohorts.csv']
    p,v,c=[pd.read_csv(ROOT/x) for x in paths];records=[]
    for cohort,split in [('PRIMARY_29',s) for s in ['observation','grouped','loso']]+[(c,s) for c in ['HEASOFT_VALIDATION','HEASOFT_MATCHED','EXPANDED_SOURCE'] for s in ['grouped','loso']]:
        census=c[c.cohort.eq(cohort)].iloc[0];row={'cohort':cohort,'split':split,'observations':int(census.observations),'sources':int(census.sources)}
        for model in ['logistic','forest']:
            frame=p if cohort=='PRIMARY_29' else v[v.cohort.eq(cohort)]
            value=frame[frame.model.eq(model)&frame.split.eq(split)].iloc[0]
            for key in ['AUROC','AUROC_lower','AUROC_upper','balanced_accuracy']:row[model+'_'+key]=float(value[key])
        records.append(row)
    frame=pd.DataFrame(records);frame.to_csv(out/'main_performance.csv',index=False)
    lines=['| Cohort / split | Observations / sources | Logistic AUROC [95% CI] | BA | Forest AUROC [95% CI] | BA |','|---|---:|---:|---:|---:|---:|']
    for r in records:
        fields=[r['cohort']+' / '+r['split'],f"{r['observations']} / {r['sources']}"]
        for model in ['logistic','forest']:
            fields.extend([f"{r[model+'_AUROC']:.3f} [{r[model+'_AUROC_lower']:.3f}, {r[model+'_AUROC_upper']:.3f}]",f"{r[model+'_balanced_accuracy']:.3f}"])
        lines.append('| '+' | '.join(fields)+' |')
    (out/'main_performance.md').write_text('\n'.join(lines)+'\n')
    (out/'input_sha256.json').write_text(json.dumps({p:sha256(ROOT/p) for p in paths},indent=2)+'\n')
    verify();print('Rebuilt 9 comparison rows from frozen summaries in build/reproduced/tables/')

if __name__=='__main__':main()
