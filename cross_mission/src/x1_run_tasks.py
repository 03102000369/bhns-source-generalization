"""Run documented NuSTARDAS tasks in new, isolated X1 work directories."""
from pathlib import Path
from paths import calibration_root
from datetime import datetime,timezone
import argparse,json,os,subprocess
ROOT=Path(__file__).resolve().parents[1]
PILOTS={'10601308002':'attempt002','30363002002':'attempt003'}

def main(obs,letter,stage):
    if obs not in PILOTS or letter not in 'AB':raise ValueError('Only existing two pilot observations allowed')
    short=ROOT
    cal=calibration_root()
    work=ROOT/f'data/processed/nustar/{obs}/x1_{letter}/{stage}'
    if work.exists():raise ValueError('Preserve old task attempt; do not overwrite')
    work.mkdir(parents=True)
    clean=short/f'data/processed/nustar/{obs}/{PILOTS[obs]}/clean'
    if stage=='exposure':
        args=['nuexpomap',f'infile={clean}/nu{obs}{letter}01_cl.evt',f'mastaspectfile={clean}/nu{obs}_mast.fits',f'attfile={clean}/nu{obs}_att.fits',f'det1reffile={clean}/nu{obs}{letter}_det1.fits','expomapfile=exposure.img','det1instrfile=det1_maps.fits','aspecthistofile=aspect_hist.fits','offsetfile=offset.fits','vignflag=no','initseed=yes','pixbin=5','clobber=no','history=yes']
    else:
        regions=short/f'data/processed/nustar/{obs}/x1_{letter}/regions'
        if not (regions/'approval.json').exists():raise ValueError('Region approval absent')
        if json.loads((regions/'approval.json').read_text())['status']!='PASS':raise ValueError('Provisional region forbidden')
        for m in 'AB':
            for d in range(4):
                if not (cal/f'data/nustar/fpm/cpf/rmf/nu{m}cutdet{d}_20100101v003.rmf').exists():raise ValueError('Required official RMF missing')
        args=['nuproducts',f'indir={clean}',f'steminputs=nu{obs}',f'instrument=FPM{letter}','outdir=out',f'srcregionfile={regions}/source.reg',f'bkgregionfile={regions}/background.reg','bkgextract=yes','runmkarf=yes','runmkrmf=yes','runbackscale=yes','rungrppha=no','arfmlicorr=no','binsize=1','barycorr=no','initseed=yes','clobber=no','history=yes','cleanup=no']
    env=os.environ.copy();env.update(PHASE2_CALDB=str(cal),PHASE2_PFILES=str(short/work.relative_to(ROOT)/'pfiles'))
    command=['bash','-c','source "$1"; shift; exec "$@"','x1',str(ROOT/'configs/nustar_env.sh'),*args]
    record=dict(obsid=obs,module='FPM'+letter,stage=stage,argv=args,started_at_utc=datetime.now(timezone.utc).isoformat(),cwd=str(work),CALDB=env['PHASE2_CALDB'],input_clean_directory=str(clean.resolve()))
    (work/'command.json').write_text(json.dumps(record,indent=2)+'\n')
    with (work/'task.log').open('w') as out:p=subprocess.run(command,cwd=work,env=env,stdout=out,stderr=subprocess.STDOUT)
    record.update(exit_code=p.returncode,finished_at_utc=datetime.now(timezone.utc).isoformat());(work/'command.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record,indent=2),flush=True)
    if p.returncode:raise RuntimeError('NuSTARDAS task failed; inspect retained log')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('obsid',choices=list(PILOTS));p.add_argument('module',choices=['A','B']);p.add_argument('stage',choices=['exposure','products']);a=p.parse_args();main(a.obsid,a.module,a.stage)
