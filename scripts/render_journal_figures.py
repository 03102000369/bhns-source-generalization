#!/usr/bin/env python3
"""Publication figures from immutable tables/predictions only; no model fitting."""
from pathlib import Path
import json, hashlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from verify_release import verify, ROOT
OUT=ROOT/'build/reproduced/figures';OUT.mkdir(parents=True,exist_ok=True)
verify()
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none','savefig.facecolor':'white'})
blue='#17638C';orange='#C85922';green='#278579';gray='#68747D'
meta=[]
def read(p):
 meta.append({'file':p,'sha256':hashlib.sha256((ROOT/p).read_bytes()).hexdigest()});return pd.read_csv(ROOT/p)
def save(fig,name):
 fig.savefig(OUT/(name+'.pdf'),bbox_inches='tight');fig.savefig(OUT/(name+'.png'),dpi=210,bbox_inches='tight');fig.savefig(OUT/(name+'.svg'),bbox_inches='tight');plt.close(fig)
p=read('results/primary_performance.csv');v=read('results/validation_heasoft/tables/validation_table_2_performance.csv');c=read('results/validation_heasoft/tables/validation_table_1_cohorts.csv')
fig,axs=plt.subplots(1,3,figsize=(12,4.4),gridspec_kw={'width_ratios':[1.2,1.2,1]})
for a,title,grouped in zip(axs[:2],['A  Observation-wise','B  Source-disjoint'],[False,True]):
 a.set_title(title,loc='left',fontweight='bold');a.set_xlim(-.25,6);a.set_ylim(-1,4.4);a.axis('off')
 a.text(1.15,3.5,'Training',ha='center');a.text(4.4,3.5,'Test',ha='center');a.axvline(3,ymin=.23,ymax=.81,color=gray,linestyle='--')
 for y,src in enumerate(['A','B','C']):
  a.text(-.2,2.7-y,src,va='center',fontweight='bold')
  positions=([.4,1.2,2] if src!='C' else [3.6,4.4,5.2]) if grouped else [.4,1.2,4.4]
  for x in positions:a.add_patch(Rectangle((x-.25,2.45-y),.5,.5,facecolor=[blue,orange,green][y],alpha=.9))
 a.text(2.8,-.5,'Same systems can occur\non both sides' if not grouped else 'Entire systems stay\non one side',ha='center',va='center')
ax=axs[2];ax.set_title('C  Cohort census',loc='left',fontweight='bold')
cc=c[c.cohort.isin(['PRIMARY_29','HEASOFT_VALIDATION','EXPANDED_SOURCE'])].set_index('cohort').loc[['PRIMARY_29','HEASOFT_VALIDATION','EXPANDED_SOURCE']]
x=np.arange(3);ax.bar(x-.16,cc.BH_sources,.3,color=blue,label='BH');ax.bar(x+.16,cc.NS_sources,.3,color=orange,label='NS')
for j,(_,r) in enumerate(cc.iterrows()):
 ax.text(j-.16,r.BH_sources+.4,str(int(r.BH_sources)),ha='center');ax.text(j+.16,r.NS_sources+.4,str(int(r.NS_sources)),ha='center');ax.text(j,27,f'{r.observations} obs.',ha='center',fontsize=9)
ax.set_xticks(x,['Primary','HEASoft','Expanded']);ax.set_ylabel('Independent physical sources');ax.set_ylim(0,30);ax.legend(frameon=False,loc='upper left',bbox_to_anchor=(0,1.01),ncol=2,fontsize=9)
fig.tight_layout(w_pad=2);save(fig,'figure_1_design')
fig,axs=plt.subplots(1,2,figsize=(10,4.4))
for ax,metric,title in zip(axs,['AUROC','balanced_accuracy'],['A  Ranking','B  Fixed-threshold classification']):
 for i,(model,color,marker) in enumerate([('logistic',blue,'o'),('forest',orange,'s')]):
  d=p[p.model.eq(model)].set_index('split').loc[['observation','grouped','loso']];x=np.arange(3)+(i-.5)*.12
  ax.errorbar(x,d[metric],yerr=[d[metric]-d[metric+'_lower'],d[metric+'_upper']-d[metric]],fmt=marker+'-',color=color,capsize=3,label=model.capitalize(),lw=1)
 ax.axhline(.5,color=gray,ls=':',lw=1);ax.set_xticks(range(3),['Observation-wise','Source-grouped','LOSO']);ax.set_ylim(.35,1.035);ax.set_ylabel('Source-level '+('AUROC' if metric=='AUROC' else 'balanced accuracy'));ax.set_title(title,loc='left',fontweight='bold');ax.grid(axis='y',alpha=.15)
axs[0].legend(frameon=False,loc='lower left');fig.tight_layout();save(fig,'figure_2_primary')
fig,axs=plt.subplots(1,2,figsize=(10,4.3),sharey=True)
for ax,path,title in zip(axs,['results/source_randomization_results.csv','results/validation_heasoft/source_randomization_results.csv'],['A  Primary','B  Independent HEASoft']):
 d=read(path)
 for i,(split,color) in enumerate([('observation',blue),('grouped',orange)]):
  a=d[d.split.eq(split)].AUROC.to_numpy();offset=np.linspace(-.16,.16,len(a));ax.scatter(i+offset,a,s=22,color=color,alpha=.6);ax.plot([i-.24,i+.24],[np.median(a)]*2,color='black',lw=2);ax.text(i,.02,f'n = {len(a)}',ha='center',fontsize=9)
 ax.set_xticks([0,1],['Observation-wise','Source-grouped']);ax.axhline(.5,color=gray,ls=':');ax.set_ylim(0,1.04);ax.set_xlim(-.5,1.5);ax.set_title(title,loc='left',fontweight='bold');ax.grid(axis='y',alpha=.15)
axs[0].set_ylabel('AUROC for randomized source labels');fig.tight_layout();save(fig,'figure_3_randomization')
fig,axs=plt.subplots(1,2,figsize=(12,4.7),sharex=True)
order=['PRIMARY_SAME_OBSIDS','HEASOFT_VALIDATION','DETECTOR_MATCHED','HEASOFT_MATCHED'];labels=['Original: identical ObsIDs','Independent HEASoft','Original: detector support','HEASoft: detector support']
for ax,split,title in zip(axs,['grouped','loso'],['A  Source-grouped','B  LOSO']):
 for i,(model,color,marker) in enumerate([('logistic',blue,'o'),('forest',orange,'s')]):
  d=v[v.model.eq(model)&v.split.eq(split)].set_index('cohort').loc[order];y=np.arange(4)+(i-.5)*.18
  ax.errorbar(d.AUROC,y,xerr=[d.AUROC-d.AUROC_lower,d.AUROC_upper-d.AUROC],fmt=marker,color=color,capsize=3,label=model.capitalize())
 ax.set_yticks(range(4),[f'{l}\n{int(c[c.cohort.eq(co)].observations.iloc[0])} obs.; 7 BH / 22 NS' for l,co in zip(labels,order)]);ax.invert_yaxis();ax.set_xlim(.48,1.025);ax.axvline(.5,color=gray,ls=':');ax.set_xlabel('Source-level AUROC');ax.set_title(title,loc='left',fontweight='bold');ax.grid(axis='x',alpha=.15)
axs[1].legend(frameon=False,loc='lower left');fig.tight_layout(w_pad=2);save(fig,'figure_4_validation')
fig,axs=plt.subplots(1,2,figsize=(11,9),sharey=True)
a=read('results/validation_heasoft/runs/EXPANDED_SOURCE_logistic_loso/source_summary.csv').sort_values(['true_class','source_name']);order=a.source_id.to_list()
for ax,model,title in zip(axs,['logistic','forest'],['A  Logistic regression','B  Random forest']):
 d=a if model=='logistic' else read('results/validation_heasoft/runs/EXPANDED_SOURCE_forest_loso/source_summary.csv').set_index('source_id').loc[order].reset_index()
 for label,color,marker in [('BH',blue,'o'),('NS',orange,'^')]:
  mask=d.true_class.eq(label).to_numpy();ax.scatter(d.p_NS[mask],np.arange(len(d))[mask],c=color,marker=marker,s=34,label=label)
 ax.axvline(.5,color=gray,ls='--');ax.set_xlim(-.025,1.025);ax.set_xlabel('Aggregate NS score');ax.set_title(title,loc='left',fontweight='bold');ax.grid(axis='x',alpha=.15)
axs[0].set_yticks(range(len(a)),a.source_name,fontsize=8.5);axs[0].invert_yaxis();axs[1].legend(frameon=False,loc='lower left');fig.tight_layout();save(fig,'figure_5_expanded')
fig,axs=plt.subplots(1,2,figsize=(11,4.5),gridspec_kw={'width_ratios':[1,1.2]})
g=read('results/state_extension/regime_feasibility.csv');ax=axs[0];x=np.arange(len(g))
for i,(cl,col) in enumerate([('BH',blue),('NS',orange)]):
 vals=g[cl+'_sources'];ax.bar(x+(i-.5)*.3,vals,.29,color=col,label=cl)
 for xx,yy in zip(x+(i-.5)*.3,vals):ax.text(xx,yy+.12,str(yy),ha='center')
ax.axhline(5,color=gray,ls='--',label='Required per class');ax.set_ylim(0,7.2);ax.set_xticks(x,['Hard-dominated','Soft-dominated']);ax.set_ylabel('Independent physical sources');ax.set_title('A  Confirmatory gate',loc='left',fontweight='bold');ax.legend(frameon=False,fontsize=9,loc='upper right')
d=read('results/state_validation/proxy_full_paired_differences.csv');d=d[d.metric.eq('AUROC')];ax=axs[1]
for i,(_,r) in enumerate(d.iterrows()):
 color=blue if r.model=='logistic' else orange;ax.errorbar(r.difference_proxy_minus_full,i,xerr=[[r.difference_proxy_minus_full-r.lower],[r.upper-r.difference_proxy_minus_full]],fmt='o',color=color,capsize=3)
ax.axvline(0,color=gray,ls='--');ax.set_yticks(range(len(d)),[r.model.capitalize()+' / '+('grouped' if r.split=='grouped' else 'LOSO') for _,r in d.iterrows()]);ax.invert_yaxis();ax.set_xlabel('AUROC difference: proxy minus full');ax.set_title('B  Proxy diagnostic',loc='left',fontweight='bold');ax.grid(axis='x',alpha=.15);fig.tight_layout(w_pad=2.5);save(fig,'figure_6_state')
(OUT/'figure_input_manifest.json').write_text(json.dumps({x['file']:x['sha256'] for x in meta},indent=2));verify();print('Rendered six figures in PNG and SVG; protected files unchanged.')
