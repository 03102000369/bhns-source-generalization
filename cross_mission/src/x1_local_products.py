"""Run products in physical space-free scratch; retain full outputs in Phase II."""
from pathlib import Path
from paths import scratch_root
import json,os,subprocess,shutil,datetime,concurrent.futures
ROOT=Path(__file__).resolve().parents[1];LOCAL=scratch_root()
def run(obs,m,bright=False):
    work=LOCAL/obs/m/('products_bright' if bright else 'products');saved=ROOT/f'data/processed/nustar/{obs}/x1_{m}'/('products_bright' if bright else 'products_local')
    if work.exists() or saved.exists():raise ValueError('New attempt required; preserve existing products')
    work.mkdir(parents=True);clean=LOCAL/obs/('bright_attempt001/clean' if bright else 'clean');regions=LOCAL/obs/m/'regions'
    if json.loads((regions/'approval.json').read_text())['status']!='PASS':raise ValueError('Unapproved regions')
    args=['nuproducts',f'indir={clean}',f'steminputs=nu{obs}',f'instrument=FPM{m}','outdir=out',f'srcregionfile={regions}/source.reg',f'bkgregionfile={regions}/background.reg','bkgextract=yes','runmkarf=yes','runmkrmf=yes','runbackscale=yes','rungrppha=no','arfmlicorr=no','binsize=1','barycorr=no','initseed=yes','clobber=no','history=yes','cleanup=yes']
    env=os.environ.copy();env['PHASE2_PFILES']=str(work/'pfiles')
    rec=dict(obsid=obs,module='FPM'+m,argv=args,physical_cwd=str(work),started_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),staging_manifest='data/manifests/x1_local_staging.json',retained_directory=str(saved))
    with (work/'task.log').open('w') as log:
        p=subprocess.run(['bash','-c','source "$1"; shift; exec "$@"','x1',str(ROOT/'configs/nustar_env.sh'),*args],cwd=work,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
    rec.update(exit_code=p.returncode,finished_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());(work/'command.json').write_text(json.dumps(rec,indent=2)+'\n')
    # Preserve all completed files; leave local verified inputs available for
    # later response checks, but the scientific product paths are in Phase II.
    shutil.copytree(work,saved);print(obs,m,p.returncode,flush=True)
    return rec
if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(2) as pool:records=list(pool.map(lambda x:run(*x),[(o,m) for o in ['10601308002','30363002002'] for m in 'AB']))
    (ROOT/'results/x1_pilot/extraction_commands.json').write_text(json.dumps(records,indent=2)+'\n')
