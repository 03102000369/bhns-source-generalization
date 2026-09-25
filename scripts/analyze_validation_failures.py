"""Literature-supported date assignments; no inferred physical states from clustering."""
from pathlib import Path
import pandas as pd
import numpy as np
from astropy.time import Time
from render_scientific_results import markdown

ROOT=Path(__file__).resolve().parents[1]
def main():
    data=pd.read_csv(ROOT/'data/processed/observations.csv');data=data[data.usable & data.source_id.isin(['xte_j1118_480','4u_1543_475','gx_339_4'])].copy()
    data['mjd']=Time(data.observation_time.to_list(),format='isot').mjd;data['state']='UNKNOWN';data['evidence_scope']='No secure observation-specific state assignment';data['reference']=''
    for i,r in data.iterrows():
        if r.source_id=='xte_j1118_480' and pd.Timestamp(r.observation_time).year in [2000,2005]:
            data.loc[i,['state','evidence_scope','reference']]=['LOW_HARD','Published outburst-wide state; not an independent timing measurement','https://arxiv.org/abs/1001.1965']
        elif r.source_id=='4u_1543_475':
            day=int(np.floor(r.mjd));state='UNKNOWN'
            if 52442<=day<=52455 or 52462<=day<=52473:state='THERMAL_DOMINANT'
            elif 52459<=day<=52461:state='STEEP_POWER_LAW'
            elif 52456<=day<=52458 or 52474<=day<=52477:state='TRANSITION'
            if state!='UNKNOWN':data.loc[i,['state','evidence_scope','reference']]=[state,'Published daily MJD interval; no extrapolation outside covered days','https://arxiv.org/abs/astro-ph/0308363']
    cols=['rxte_obsid','source_id','canonical_source','observation_time','mjd','state','evidence_scope','reference']
    p=pd.read_csv(ROOT/'results/loso_predictions.csv');p=p[p.model.isin(['logistic','forest'])]
    f=data[cols].merge(p,left_on=['rxte_obsid','source_id'],right_on=['obs_id','source_id'],validate='one_to_many');f['correct']=f.p_NS.lt(.5)
    f.to_csv(ROOT/'results/validation_heasoft/loso_state_annotations.csv',index=False)
    g=f.groupby(['source_id','model','state']).agg(observations=('obs_id','size'),fraction_correct=('correct','mean'),mean_p_NS=('p_NS','mean')).reset_index();g.to_csv(ROOT/'results/validation_heasoft/state_failure_summary.csv',index=False)
    summary=data.groupby(['canonical_source','state']).size().rename('observations').reset_index()
    (ROOT/'reports/validation_heasoft/loso_astrophysical_failure_analysis.md').write_text('''# Astrophysical analysis of difficult primary LOSO sources

These annotations are independent literature context for the frozen predictions. They are not new training labels. The primary forest correctly classified 0/22 XTE J1118+480 observations, 3/16 4U 1543-47 observations, and 8/22 GX 339-4 observations.

**FACT — XTE J1118+480.** The sampled dates are March–July 2000 and January 2005. [Brocksopp et al.](https://arxiv.org/abs/1001.1965) describe both outbursts as remaining in the low/hard state, while their multiwavelength disc/jet contributions differed. We therefore attach an outburst-level LOW_HARD annotation to these 22 rows, explicitly distinct from a fresh timing-based state classification. [Hynes et al.](https://arxiv.org/abs/astro-ph/0005398) studied the low-state 2000 mini-outburst; the high Galactic latitude and low absorption make the broadband source unusually accessible. No quantitative inclination effect is estimated here.

**FACT — 4U 1543-47.** The dataset samples June 17–August 3, 2002. [Park et al.](https://arxiv.org/abs/astro-ph/0308363), sections 3.1–3.2, report thermal-dominant intervals at MJD 52442–52455 and 52462–52473, a steep-power-law interval at 52459–52461, and transition intervals in between and at 52474–52477. We assign only those explicitly covered dates. Their low orbital inclination is approximately 21 degrees. They fixed absorbing column to 4e21 cm^-2 because these PCA spectra did not constrain it well; that adopted fit value is not a new measurement. Later sampled dates remain UNKNOWN here.

**FACT — GX 339-4.** The selected observations span 1996–2011 and several outbursts. [Belloni et al.](https://arxiv.org/abs/astro-ph/0504577) established multiple spectral/timing states in the 2002/2003 RXTE outburst; [Motta et al.](https://arxiv.org/abs/0810.3556) investigated the 2007 transition. The literature establishes state diversity, but year/outburst membership alone cannot identify the state of each selected ObsID. These 22 rows remain UNKNOWN. Absorption, inclination and reflection require observation-specific modeling; they are not explanations established by our classifier.

**HYPOTHESES.** Hard-state spectral overlap with NS emission, sampling of different disc contributions, inclination, and incomplete instrument correction could contribute to failures. The current outputs do not distinguish these causes. In particular, failure for a BH source does not mean its physical nature is uncertain.

## Exploratory state-linked failure counts

'''+markdown(summary)+'\n\n'+markdown(g)+'''

Fractions summarize dependent observations within a source. Only two sources have any supported state annotation, with different assignment scopes and no equivalent NS state labels. A source-independent comparison of BH/NS discrimination by physical state is therefore **INFEASIBLE** in this stage. No clustering or arbitrary hardness threshold was renamed as a physical state.
''')
    print(summary.to_string(index=False))

if __name__=='__main__':main()
