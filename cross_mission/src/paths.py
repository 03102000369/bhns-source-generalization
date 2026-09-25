"""Portable development locations; no workstation-specific defaults."""
from pathlib import Path
import os
ROOT=Path(__file__).resolve().parents[1]

def scratch_root():
    return Path(os.environ.get('BHNS_NUSTAR_WORK',str(ROOT/'build/nustar_work'))).expanduser().resolve()

def calibration_root():
    value=os.environ.get('PHASE2_CALDB') or os.environ.get('CALDB')
    if not value:raise ValueError('Set PHASE2_CALDB or CALDB to the installed official calibration tree')
    path=Path(value).expanduser().resolve()
    if not path.is_dir():raise ValueError('Local CALDB directory is absent')
    return path

def resolve_product_path(value):
    path=Path(value)
    if path.is_absolute() or '..' in path.parts:raise ValueError('Gate product paths must be relative to cross_mission')
    prefix=Path('data/processed/nustar')
    override=os.environ.get('BHNS_NUSTAR_PRODUCTS_ROOT')
    if override and path.is_relative_to(prefix):return Path(override).expanduser().resolve()/path.relative_to(prefix)
    return ROOT/path

def pilot_output():
    out=Path(os.environ.get('BHNS_X2_OUTPUT',str(ROOT/'build/x2_pilot'))).expanduser().resolve()
    if out==ROOT/'results/x2_pilot':raise ValueError('Use a new output directory; preserve the packaged pilot evidence')
    return out
