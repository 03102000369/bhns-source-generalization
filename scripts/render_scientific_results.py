"""Render static publication figures/tables only from completed real experiments."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build/reproduced/primary_figures'
COLORS={'BH':'#32688e','NS':'#b57522'}


def markdown(frame):
    columns=list(frame.columns)
    def fmt(v):
        if pd.isna(v):return '—'
        return f'{v:.3f}' if isinstance(v,float) else str(v).replace('|',' / ')
    return '| '+' | '.join(columns)+' |\n|'+'|'.join(['---']*len(columns))+'|\n'+'\n'.join('| '+' | '.join(fmt(r[c]) for c in columns)+' |' for r in frame.to_dict('records'))+'\n'


def save(fig,name):
    fig.savefig(OUT/(name+'.pdf'),bbox_inches='tight')
    fig.savefig(OUT/(name+'.png'),dpi=220,bbox_inches='tight')
    plt.close(fig)


def main():
    from verify_release import verify
    verify()
    OUT.mkdir(parents=True,exist_ok=True);tables=ROOT/'build/reproduced/primary_tables';tables.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                         'axes.titlesize':12,'axes.labelsize':10,'pdf.fonttype':42,'savefig.facecolor':'white'})
    obs=pd.read_csv(ROOT/'data/processed/observations.csv');usable=obs[obs.usable]
    census=usable.groupby(['source_id','canonical_source','class_label']).size().rename('observations').reset_index()
    perf=pd.read_csv(ROOT/'results/primary_performance.csv');loso=pd.read_csv(ROOT/'results/loso_source_summary.csv')
    null=pd.read_csv(ROOT/'results/source_randomization_results.csv');curve=pd.read_csv(ROOT/'results/source_learning_curve.csv')
    robust=pd.read_csv(ROOT/'results/robustness_results.csv');identity=pd.read_csv(ROOT/'results/source_identification_predictions.csv')
    fig,ax=plt.subplots(1,2,figsize=(7.2,3.3),layout='constrained')
    for axis,counts,title in [(ax[0],census.class_label.value_counts(),'Independent physical sources'),(ax[1],usable.class_label.value_counts(),'Pointed observations')]:
        values=[counts.get(c,0) for c in ['BH','NS']];axis.bar(['BH','NS'],values,color=[COLORS[c] for c in ['BH','NS']],width=.58)
        for i,v in enumerate(values):axis.text(i,v+max(values)*.025,str(v),ha='center')
        axis.set(title=title,ylabel='Count',ylim=(0,max(values)*1.17))
    save(fig,'figure_1_cohort')
    fig,axes=plt.subplots(1,2,figsize=(8.8,3.8),layout='constrained')
    modes=['observation','grouped','loso'];labels=['Observation\noverlap','Source\ngrouped','LOSO']
    for ax,metric in zip(axes,['AUROC','balanced_accuracy']):
        for model,color,offset in [('prior','#888888',-.12),('logistic','#32688e',0),('forest','#27857a',.12)]:
            g=perf[perf.model.eq(model)].set_index('split').loc[modes];x=np.arange(3)+offset
            ax.vlines(x,g[metric+'_lower'],g[metric+'_upper'],color=color,lw=1.2)
            ax.plot(x,g[metric],'-o',color=color,label=model,ms=4,lw=1)
        ax.axhline(.5,color='#777777',ls=':',lw=.8);ax.set(xticks=np.arange(3),xticklabels=labels,ylabel=metric.replace('_',' '),ylim=(-.02,1.03))
        ax.grid(axis='y',alpha=.15)
    axes[0].legend(frameon=False,fontsize=8,loc='lower left');save(fig,'figure_2_split_comparison')
    g=loso[loso.model.eq('forest')].sort_values(['true_class','fraction_correct','source_name']).copy()
    g['correct_score']=np.where(g.true_class.eq('NS'),g.p_NS,1-g.p_NS)
    y=np.arange(len(g));fig,ax=plt.subplots(figsize=(7.6,max(6.5,.27*len(g))),layout='constrained')
    ax.barh(y,g.correct_score,color=[COLORS[c] for c in g.true_class],alpha=.75,label='Aggregated score for true class')
    ax.scatter(g.fraction_correct,y,c='#202020',marker='|',s=80,label='Fraction of observations correct',zorder=3)
    ax.axvline(.5,color='#777777',ls=':',lw=.9);ax.set(yticks=y,yticklabels=[f'{n} ({c}; n={k})' for n,c,k in zip(g.source_name,g.true_class,g.n_observations)],xlim=(0,1.02),xlabel='Held-out performance / score')
    ax.legend(frameon=False,fontsize=8,loc='lower right');ax.tick_params(axis='y',labelsize=8)
    save(fig,'figure_3_loso_sources')
    fig,ax=plt.subplots(figsize=(6.8,3.6),layout='constrained')
    for mode,color in [('observation','#32688e'),('grouped','#b57522')]:
        ax.hist(null[null.split.eq(mode)].AUROC,bins=np.linspace(0,1,16),histtype='step',lw=2,label=mode+' (50 source permutations)',color=color)
    ax.axvline(.5,color='#555555',ls=':',lw=1);ax.set(xlabel='Source-level AUROC against randomized targets',ylabel='Permutations',xlim=(0,1));ax.legend(frameon=False,fontsize=8)
    save(fig,'figure_4_source_randomization')
    fig,axes=plt.subplots(1,2,figsize=(8.2,3.5),layout='constrained')
    for ax,metric in zip(axes,['AUROC','balanced_accuracy']):
        jitter=np.random.default_rng(42).uniform(-.12,.12,len(curve))
        ax.scatter(curve.training_sources+jitter,curve[metric],s=10,color='#777777',alpha=.45,label='Fold/subsample results')
        stats=curve.groupby('training_sources')[metric].agg(['median',lambda x:x.quantile(.1),lambda x:x.quantile(.9)])
        x=stats.index.to_numpy();ax.fill_between(x,stats.iloc[:,1],stats.iloc[:,2],color='#32688e',alpha=.18,label='10–90% empirical spread')
        ax.plot(x,stats['median'],'o-',color='#32688e',label='Median');ax.axhline(.5,color='#777777',ls=':',lw=.8)
        ax.set(xlabel='Unique training sources (equal BH/NS)',ylabel=metric.replace('_',' '),ylim=(0,1.03),xticks=x)
    axes[0].legend(frameon=False,fontsize=8);save(fig,'figure_5_source_learning_curve')
    baseline=perf[perf.model.eq('logistic')&perf.split.eq('grouped')].iloc[0];sem=robust[robust.analysis.eq('SEM_same_cohort')].iloc[0]
    fig,ax=plt.subplots(figsize=(5.7,3.6),layout='constrained')
    for x,row,color in [(0,baseline,'#32688e'),(1,sem,'#27857a')]:
        ax.bar(x,row.AUROC,color=color,width=.5);ax.vlines(x,row.AUROC_lower,row.AUROC_upper,color='black',lw=1.2)
    ax.set(xticks=[0,1],xticklabels=['43 spectral rates','43 rates + 43 errors'],ylim=(0,1.03),ylabel='Source-grouped AUROC (logistic)')
    ax.axhline(.5,color='#777777',ls=':',lw=.8);save(fig,'figure_6_feature_comparison')
    identification=identity.groupby('source_id').correct.mean().sort_values()
    names=census.set_index('source_id').canonical_source
    fig,ax=plt.subplots(figsize=(7,max(6,.25*len(identification))),layout='constrained')
    y=np.arange(len(identification));ax.barh(y,identification,color='#647b8f');ax.axvline(1/len(identification),color='#333333',ls=':',label='Uniform source guess')
    ax.set(yticks=y,yticklabels=[names.loc[s] for s in identification.index],xlabel='Fraction assigned to the correct source',xlim=(0,1));ax.tick_params(axis='y',labelsize=8);ax.legend(frameon=False,fontsize=8)
    save(fig,'figure_7_source_identification')
    roster=pd.read_csv(ROOT/'data/reference/reference_source_roster.csv').fillna('')
    table1=roster[['reference_source_name','canonical_source_name','source_id','reference_class','class_label','classification_status','classification_reference']].copy()
    counts=census.set_index('source_id').observations
    table1['usable_observations']=table1.source_id.map(counts).fillna(0).astype(int)
    table1['inclusion_status']=np.where(table1.usable_observations.gt(0),'INCLUDED','EXCLUDED / UNRESOLVED')
    table1.to_csv(tables/'table_1_dataset.csv',index=False)
    (tables/'table_1_dataset.md').write_text('# Table 1 — source roster\n\nDuplicate reference designations for V4641 Sgr share one physical source; do not add their counts.\n\n'+markdown(table1.drop(columns=['source_id'])))
    table2=perf[['model','split','sources','observations']].copy()
    for metric in ['AUROC','balanced_accuracy','MCC','F1']:
        table2[metric+' [95% CI]']=[f'{r[metric]:.3f} [{r[metric+"_lower"]:.3f}, {r[metric+"_upper"]:.3f}]' for r in perf.to_dict('records')]
    table2.to_csv(tables/'table_2_primary_performance.csv',index=False);(tables/'table_2_primary_performance.md').write_text('# Table 2 — source-primary performance\n\n'+markdown(table2))
    feature_rows=[dict(representation='spectra',status='COMPLETED',sources=int(baseline.sources),observations=int(baseline.observations),AUROC=baseline.AUROC,lower=baseline.AUROC_lower,upper=baseline.AUROC_upper),
                  dict(representation='spectra + errors',status='COMPLETED; same cohort',sources=int(sem.sources),observations=int(sem.observations),AUROC=sem.AUROC,lower=sem.AUROC_lower,upper=sem.AUROC_upper),
                  dict(representation='PM',status='UNAVAILABLE OPTIONAL'),dict(representation='spectra + PM',status='UNAVAILABLE OPTIONAL')]
    table3=pd.DataFrame(feature_rows);table3.to_csv(tables/'table_3_features.csv',index=False);(tables/'table_3_features.md').write_text('# Table 3 — source-grouped logistic feature comparison\n\n'+markdown(table3))
    cols=['analysis','sources','observations','AUROC','AUROC_lower','AUROC_upper','balanced_accuracy','MCC','F1']
    robust[cols].to_csv(tables/'table_4_robustness.csv',index=False);(tables/'table_4_robustness.md').write_text('# Table 4 — predefined sensitivities\n\nNo provisional sources entered the primary analysis, so removing provisional systems leaves the same cohort. These sensitivities do not redefine the primary model.\n\n'+markdown(robust[cols]))
    captions={
      1:'Unique physical systems and individual pointed observations are shown separately. Source counts define the independent sample size.',
      2:'Identical eligible cohort, source-aggregated OOF scores. Whiskers are 95% class-stratified source-bootstrap percentile intervals (2,000 draws), conditional on fitted predictions. Observation folds intentionally allow source overlap; grouped and LOSO folds do not.',
      3:'Random-forest LOSO results for each entirely held-out physical source. Bars give the mean-log-odds score for its true class; ticks give the fraction of its observations classified correctly. Scores are not asserted to be calibrated posterior probabilities. n denotes observations.',
      4:'Fifty source-label permutations preserve one randomized class per physical source and the source class counts. The same fixed forest is evaluated under observation and source-grouped OOF splits. The dotted line marks AUROC 0.5. Distributions are diagnostic controls, not uncertainty intervals for the true-label scores.',
      5:'Fixed-C logistic learning curves use 2, 3 or 5 training sources per class when feasible, with five source-subsampling seeds and fixed outer grouped test sources. Shading is empirical 10–90% spread across dependent fold/subsample results, not a confidence interval or independent repeated experiment.',
      6:'Source-grouped logistic regression on the identical source/observation cohort, comparing 43 recorded spectral rates with the same rates plus formal archive statistical errors. Whiskers are source-bootstrap 95% intervals. PM features were unavailable.',
      7:'Exploratory source identification using a fixed random forest and three observation folds stratified by physical source. Bars show per-source correct fractions; the dotted line is uniform guessing among eligible source identities. This diagnostic does not establish the physical cause of source fingerprints.'}
    (OUT/'captions.md').write_text('# Figure captions\n\n'+'\n\n'.join(f'**Figure {k}.** {v}' for k,v in captions.items())+'\n')
    print('Rendered seven figure pairs and four manuscript tables')


if __name__=='__main__':main()
