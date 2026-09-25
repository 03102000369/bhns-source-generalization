"""Explicit distributable-payload scope shared by release tools."""
from pathlib import Path
import hashlib
ROOT=Path(__file__).resolve().parents[1]
CONTROL={'RELEASE_MANIFEST.csv','RELEASE_MANIFEST.sha256'}
LOCAL={'github_release_file_inventory.csv','github_release_large_files.csv'}
OMIT_DIRS={'.git','.release_audit','.local_admin','build','dist','.venv','venv','__pycache__','.pytest_cache','.mypy_cache','.ruff_cache'}

def sha256(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def payload(root=ROOT):
    import os
    for base,dirs,files in os.walk(root,followlinks=False):
        dirs[:]=sorted(d for d in dirs if d not in OMIT_DIRS and not d.endswith('.egg-info'))
        for name in sorted(files):
            p=Path(base)/name;rel=p.relative_to(root).as_posix()
            if rel in CONTROL|LOCAL or name=='.DS_Store' or name.endswith(('.pyc','.pyo')):continue
            if p.is_symlink():raise ValueError('Symlink outside payload policy: '+rel)
            yield p

def describe(rel):
    phase='II' if rel.startswith('cross_mission/') else ('I' if rel.startswith(('src/','configs/','data/','results/','manuscript/')) else 'shared')
    category=rel.split('/')[0] if '/' in rel else 'release_metadata'
    role={'src':'analysis implementation','scripts':'reproduction or release tooling','configs':'protocol or configuration','data':'tabular cohort, source identity or acquisition provenance','results':'frozen scientific output','manuscript':'publication source or artifact','tests':'software/scientific integrity contract','cross_mission':'unfinished separate cross-mission study','docs':'scientific and reproduction guidance'}.get(category,'release administration and audit')
    return phase,category,role
