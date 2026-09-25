"""Stage immutable L1 bytes, then run both modules through real NuSTARDAS."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import gzip
import json
import shutil
import subprocess
import os
from evidence import ROOT, sha256

def main(obsid, attempt, saamode='NONE', tentacle='no'):
    work=ROOT/f'data/processed/nustar/{obsid}/{attempt}'
    if work.exists():raise RuntimeError('Attempt already exists; preserve it and use a new attempt ID')
    manifest=json.loads((ROOT/f'data/manifests/download_{obsid}.json').read_text())
    if len(manifest)<10:raise ValueError('Incomplete raw download manifest')
    work.mkdir(parents=True)
    inputs=[]
    for item in manifest:
        src=ROOT/item['path']
        if sha256(src)!=item['sha256']:raise ValueError('Raw product hash mismatch')
        rel=src.relative_to(ROOT/f'data/raw/nustar/{obsid}')
        dst=work/'input'/rel
        if dst.suffix=='.gz':dst=dst.with_suffix('')
        dst.parent.mkdir(parents=True,exist_ok=True)
        if src.suffix=='.gz':
            with gzip.open(src,'rb') as fi,dst.open('wb') as fo:shutil.copyfileobj(fi,fo)
        else:shutil.copyfile(src,dst)
        inputs.append(dict(path=str(dst.relative_to(ROOT)),sha256=sha256(dst),raw_sha256=item['sha256']))
    (work/'staged_inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
    args=['nupipeline','indir=input',f'steminputs=nu{obsid}','outdir=clean','instrument=ALL','obsmode=SCIENCE','entrystage=1','exitstage=2',f'saamode={saamode}','saacalc=3',f'tentacle={tentacle}','statusexpr=DEFAULT','clobber=no','history=yes']
    rec=dict(obsid=obsid,attempt=attempt,started_at_utc=datetime.now(timezone.utc).isoformat(),cwd=str(work),argv=args,caldb=os.environ.get('PHASE2_CALDB','https://nasa-heasarc.s3.us-east-1.amazonaws.com/caldb'),modules=['FPMA','FPMB'])
    (work/'command.json').write_text(json.dumps(rec,indent=2)+'\n')
    envfile=ROOT/'configs/nustar_env.sh'
    # Positional shell arguments preserve spaces without shell interpolation.
    command=['bash','-c','export PHASE2_PFILES="$PWD/pfiles"; source "$1"; shift; exec "$@"','phase2',str(envfile),*args]
    with (work/'nupipeline.log').open('w') as log:
        result=subprocess.run(command,cwd=work,stdout=log,stderr=subprocess.STDOUT)
    rec.update(finished_at_utc=datetime.now(timezone.utc).isoformat(),exit_code=result.returncode)
    rec['module_events']={module:dict(path=f'clean/nu{obsid}{letter}01_cl.evt',exists=(work/f'clean/nu{obsid}{letter}01_cl.evt').is_file()) for module,letter in [('FPMA','A'),('FPMB','B')]}
    (work/'command.json').write_text(json.dumps(rec,indent=2)+'\n')
    print(json.dumps(rec,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('obsid');p.add_argument('--attempt',default='attempt001');p.add_argument('--saamode',choices=['NONE','OPTIMIZED','STRICT'],default='NONE');p.add_argument('--tentacle',choices=['yes','no'],default='no');a=p.parse_args();main(a.obsid,a.attempt,a.saamode,a.tentacle)
