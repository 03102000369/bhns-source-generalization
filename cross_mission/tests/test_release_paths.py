"""Resolve accepted gate evidence without silently changing input identity."""
from pathlib import Path
import json,sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from paths import ROOT,resolve_product_path,pilot_output

def test_all_accepted_product_paths_are_portable_and_unique(monkeypatch,tmp_path):
    gate=json.loads((ROOT/'reports/gate_x1_report.json').read_text())
    original=[];moved=[]
    monkeypatch.delenv('BHNS_NUSTAR_PRODUCTS_ROOT',raising=False)
    for row in gate['modules']:
        for key,value in row['paths'].items():
            path=resolve_product_path(value)
            assert path.is_relative_to(ROOT/'data/processed/nustar')
            assert len(row['hashes'][key])==64
            original.append(path)
    monkeypatch.setenv('BHNS_NUSTAR_PRODUCTS_ROOT',str(tmp_path))
    for row in gate['modules']:
        for value in row['paths'].values():
            path=resolve_product_path(value);assert path.is_relative_to(tmp_path);moved.append(path)
    assert len(original)==len(set(original))==16
    assert [p.relative_to(ROOT/'data/processed/nustar') for p in original]==[p.relative_to(tmp_path) for p in moved]

@pytest.mark.parametrize('path',['/outside/source.pha','../source.pha','data/../../source.pha'])
def test_unsafe_gate_path_is_rejected(path):
    with pytest.raises(ValueError):resolve_product_path(path)

def test_measurement_attempt_cannot_replace_packaged_pilot(monkeypatch):
    monkeypatch.setenv('BHNS_X2_OUTPUT',str(ROOT/'results/x2_pilot'))
    with pytest.raises(ValueError,match='preserve'):pilot_output()
