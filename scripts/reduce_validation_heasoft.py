"""Run documented RXTE preparation/extraction commands with per-ObsID provenance."""
import argparse,json,os,shutil,subprocess,traceback,concurrent.futures
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd
from astropy.io import fits
from bhns.data.instrument_validation import *
from bhns.data.rxte_products import designation_key

ROOT=Path(__file__).resolve().parents[1]

def reduce_one(row):
    obs=row['rxte_obsid'];out=validation_path(ROOT,'data/processed/validation_heasoft/reduction/'+obs);out.mkdir(parents=True,exist_ok=True)
    record_path=out/'processing.json';_,ph=validation_protocol(ROOT)
    if record_path.exists():
        rec=json.loads(record_path.read_text())
        if rec.get('status')=='COMPLETE':
            if rec['protocol_sha256']!=ph or any(sha256(out/p)!=h for p,h in rec['outputs'].items()):raise ValueError('Changed reduction checkpoint')
            return rec
        if rec.get('status')=='EXCLUDED_ZERO_GTI':return rec
        history=out/'attempt_history';history.mkdir(exist_ok=True)
        (history/f'processing_{len(list(history.glob("*.json"))):03d}.json').write_bytes(record_path.read_bytes())
    attempt=len(list((out/'attempt_history').glob('*.json')))
    rec=dict(rxte_obsid=obs,source_id=row['source_id'],source_name=row['canonical_source'],class_label=row['class_label'],protocol_sha256=ph,status='FAILED',commands=[])
    try:
        manifest=ROOT/'data/provenance/validation_heasoft/raw'/obs/'download_manifest.json';raw=json.loads(manifest.read_text())
        if raw['status']!='COMPLETE':raise ValueError('Original archive inputs incomplete')
        if any(sha256(f['path'])!=f['sha256'] for f in raw['files']):raise ValueError('Archive input checksum mismatch')
        with fits.open(ROOT/'data/raw/validation_heasoft'/obs/'FMI') as index:
            rows=index['XTE_MI'].data
            if set(str(x).strip() for x in rows['ObsId'])!={obs}:raise ValueError('FMI ObsID identity mismatch')
        registry=pd.read_csv(ROOT/'data/reference/reference_source_roster.csv');targets=registry[registry.source_id.eq(row['source_id'])]
        if len(targets):
            aliases=set(a for v in targets.aliases for a in str(v).split('|'));ra0=float(targets.iloc[0].ra_deg);dec0=float(targets.iloc[0].dec_deg)
        else:
            target=next(x for x in json.loads((ROOT/'results/validation_heasoft/bh_expansion_evidence.json').read_text()) if x['source_id']==row['source_id']);aliases=set(target['aliases'].split('|'));ra0=target['ra_deg'];dec0=target['dec_deg']
        identity_addenda=ROOT/'data/provenance/validation_heasoft/identity_addenda.json'
        if identity_addenda.exists():
            for addition in json.loads(identity_addenda.read_text()):
                if addition['source_id']==row['source_id'] and obs in addition['rxte_obsids']:
                    aliases.add(addition['archive_alias']);rec['identity_addenda_sha256']=sha256(identity_addenda)
        if any(designation_key(x) not in {designation_key(a) for a in aliases} for x in rows['Source']):raise ValueError('Unreviewed archive FMI target identity')
        from astropy.coordinates import SkyCoord
        import astropy.units as u
        if np.any(SkyCoord(rows['RA']*u.deg,rows['Dec']*u.deg).separation(SkyCoord(ra0*u.deg,dec0*u.deg)).deg>.05):raise ValueError('FMI pointing fails independent position check')
        rec['raw_manifest_sha256']=sha256(manifest);rec['caldb_manifest_sha256']=sha256(ROOT/'results/validation_heasoft/caldb_installation.json')
        rec['software_environment_sha256']=sha256(ROOT/'results/validation_heasoft/software_environment.json')
        # xtedatamode's documented default scans both detector directories even
        # when pcaprepobsid processes PCA only. This empty directory contains no
        # fabricated HEXTE files and changes none of the archived input bytes.
        (ROOT/'data/raw/validation_heasoft'/obs/'hexte').mkdir(exist_ok=True)
        for f in (ROOT/'data/raw/validation_heasoft'/obs/'pca').glob('FS4[6a]*'):
            with fits.open(f,memmap=False) as h:
                mode=h[1].header.get('DATAMODE',h[0].header.get('DATAMODE',''))
                if 'Standard' not in mode:raise ValueError('Downloaded file prefix does not identify Standard1/2 mode')
        env=os.environ.copy();(out/'pfiles').mkdir(exist_ok=True);env['PFILES']=str(out/'pfiles')+';'+str(Path(env['HEADAS'])/'syspfiles')
        env.update(HEADASNOQUERY='',HEADASPROMPT='/dev/null')
        if os.uname().sysname=='Darwin':
            env['PATH']=str(ROOT/'scripts/validation_compat')+os.pathsep+env['PATH']
            rec['macos_zcat_compatibility_sha256']=sha256(ROOT/'scripts/validation_compat/zcat')
        def execute(args):
            log=out/(f'a{attempt:02d}_{len(rec["commands"]):02d}_'+args[0]+'.log')
            c=dict(argv=args,cwd=str(out),started_at=datetime.now(timezone.utc).isoformat(),log=str(log),executable=shutil.which(args[0]))
            with log.open('w') as stream:run=subprocess.run(args,cwd=out,env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,timeout=600)
            c.update(exit_code=run.returncode,log_sha256=sha256(log));rec['commands'].append(c)
            if run.returncode:raise RuntimeError(f'{args[0]} exited {run.returncode}: {log}')
        rawrel=os.path.relpath(ROOT/'data/raw/validation_heasoft'/obs,out)
        execute(['pcaprepobsid','indir='+rawrel,'outdir=prepared','modelfile=CALDB','datamodes=Standard1,Standard2','clobber=YES'])
        if not (out/'prepared/pcaprepobsid_done.txt').exists():raise ValueError('pcaprepobsid success sentinel missing')
        filt=(out/'prepared/FP_xtefilt.lis').read_text().splitlines()[0].strip()
        expr=screening_expression(gain_epoch(row['observation_time']))
        execute(['maketime','infile='+filt,'outfile=screened.gti','expr='+expr,'name=NAME','value=VALUE','time=TIME','prefr=0.5','postfr=0.5','compact=NO','emptygti=APPLY','clobber=YES'])
        with fits.open(out/'screened.gti') as h:
            g=h[1].data
            if not len(g) or np.sum(g['STOP']-g['START'])<=0:raise ValueError('ZERO_GOOD_EXPOSURE: predeclared conservative GTI rejects this observation')
        execute(['pcaextspect2','src_infile=@prepared/FP_dtstd2.lis','bkg_infile=@prepared/FP_dtbkg2.lis','src_phafile=source.pha','bkg_phafile=background.pha','gtiandfile=screened.gti','pculist=2','layerlist=1','respfile=response.rsp','filtfile='+filt,'clobber=YES'])
        arrays,meta=heasoft_spectrum(out/'source.pha',out/'background.pha',out/'response.rsp')
        # Input tree is ObsID-verified; bind source identity again to the resulting PHA.
        with fits.open(out/'source.pha') as h:
            header=h['SPECTRUM'].header;meta['object']=header.get('OBJECT');meta['deadapp']=header.get('DEADAPP');meta['selected_rowids']=[str(v) for k,v in header.items() if k.startswith('ROWID')]
            if designation_key(meta['object']) not in {designation_key(a) for a in aliases}:raise ValueError('Extracted PHA source identity mismatch')
        with fits.open(out/'screened.gti') as h:
            g=h[1].data;meta['screened_gti_seconds']=float(np.sum(g['STOP']-g['START']))
        np.savez_compressed(out/'native.npz',**arrays)
        rec.update(status='COMPLETE',metadata=meta,screening_expression=expr,representation='HEASOFT_CALDB_RATE43_V1',outputs={p:sha256(out/p) for p in ['source.pha','background.pha','response.rsp','screened.gti','native.npz']})
    except Exception as e:
        rec.update(error=str(e),traceback=traceback.format_exc())
        if 'ZERO_GOOD_EXPOSURE' in str(e):rec['status']='EXCLUDED_ZERO_GTI'
    record_path.write_text(json.dumps(rec,indent=2));print(obs,rec['status'],rec.get('error',''),flush=True);return rec

def main():
    a=argparse.ArgumentParser();a.add_argument('--obsid');a.add_argument('--expanded',action='store_true');a.add_argument('--available-only',action='store_true');a.add_argument('--workers',type=int,default=2);args=a.parse_args();verify_primary(ROOT)
    required=['pcaprepobsid','pcaextspect2','maketime','pcarsp','pcadeadcalc2','pcabackest']
    if any(shutil.which(t) is None for t in required):raise RuntimeError('Initialize the HEASoft environment first')
    selection=ROOT/'data/processed/validation_heasoft'/('expanded_selection.csv' if args.expanded else 'preselected_observations.csv');f=pd.read_csv(selection)
    if args.obsid:f=f[f.rxte_obsid.eq(args.obsid)]
    if args.available_only:
        available=[]
        for obs in f.rxte_obsid:
            p=ROOT/'data/provenance/validation_heasoft/raw'/obs/'download_manifest.json'
            if p.exists() and json.loads(p.read_text())['status']=='COMPLETE':available.append(obs)
        f=f[f.rxte_obsid.isin(available)]
    with concurrent.futures.ThreadPoolExecutor(args.workers) as pool:results=list(pool.map(reduce_one,f.to_dict('records')))
    summary_name='expanded_reduction_summary.json' if args.expanded else 'reduction_summary.json'
    (ROOT/'results/validation_heasoft'/summary_name).write_text(json.dumps(dict(attempted=len(results),complete=sum(x['status']=='COMPLETE' for x in results),failures=[dict(rxte_obsid=x['rxte_obsid'],error=x.get('error')) for x in results if x['status']!='COMPLETE']),indent=2));verify_primary(ROOT)

if __name__=='__main__':main()
