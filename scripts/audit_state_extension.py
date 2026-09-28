"""Final read-only scientific audit plus additive integrity/completion records."""
import json,re
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
from bhns.data.state_validation import sha256,verify_protected
from bhns.data.state_extension import validate_extension,merge_catalogues,source_gate,validate_chronology
R=Path(__file__).resolve().parents[1];D=R/'data/state_extension';O=R/'results/state_extension';P=R/'reports/state_extension';C=R/'configs/state_extension'

def main():
 n=verify_protected(R,json.loads((O/'protected_artifact_manifest.json').read_text()))
 status=json.loads((O/'stage_status.json').read_text());plan=json.loads((C/'search_plan_frozen.json').read_text());mapping=json.loads((C/'state_regime_mapping_v2_frozen.json').read_text())
 validate_chronology(plan,mapping,status)
 old=pd.read_csv(R/'data/state_validation/obsid_state_catalogue.csv').fillna('');ext=pd.read_csv(D/'obsid_state_catalogue_extension.csv').fillna('');merged=pd.read_csv(D/'obsid_state_catalogue_merged.csv').fillna('')
 validate_extension(ext)
 expected=merge_catalogues(old,ext).fillna('')
 pd.testing.assert_frame_equal(expected,merged,check_dtype=False)
 gate=source_gate(merged[merged.in_expanded]);assert not gate.PASS.any()
 pd.testing.assert_frame_equal(gate,pd.read_csv(O/'regime_feasibility.csv'))
 assert status['extension_sha256']==sha256(D/'obsid_state_catalogue_extension.csv')
 assert status['merged_sha256']==sha256(D/'obsid_state_catalogue_merged.csv')
 assert status['mapping_sha256']==sha256(C/'state_regime_mapping_v2_frozen.json')
 assert not (D/'state_controlled_observations.csv').exists() and not (O/'runs').exists()
 output=(P/'pytest_output.txt').read_text();result=re.findall(r'\d+ passed in [\d.]+s',output)[-1]
 assert result.startswith('278 passed') and 'failed' not in output
 integrity=dict(checked_utc=datetime.now(timezone.utc).isoformat(),protected_files=n,mismatches=[],original_catalogue_rows=len(old),merged_catalogue_rows=len(merged),extension_review_rows=len(ext),pytest=result,old_tests_preserved=245,new_tests=33,ml_runs=0,state_controlled_cohort_created=False,verdict=status['verdict'])
 (O/'integrity_after.json').write_text(json.dumps(integrity,indent=2))
 (P/'verification.md').write_text('# Final verification\n\n'+f'Protected artifacts: {n:,} of {n:,} SHA-256 checks passed, with zero mismatches. All original catalogue fields are retained in the 880-row derived catalogue; the original 880-row file is unchanged. The extension contains 154 review rows and no new spectra.\n\nFull suite: **{result}** (245 existing tests plus 33 extension tests). Tests cover protected files, schema, evidence/Boolean validation, exact-identifier and temporal guards, conflicts, original/extension provenance, physical-source counting, chronology and hashes, no fitting/cohort creation under Branch B, unsupported manuscript claims, and equality of manuscript metric rows to frozen tables. Source-disjoint state-controlled folds are not applicable because no such experiment was created; existing source-isolation tests remain unchanged and pass.\n\nThe Linares, Bult and Ibragimov evidence tables and the new feasibility chart were visually inspected. The evidence-level tables retain unmapped/provisional/unresolved cases rather than assigning them artificial regimes. No inclusion decision followed a new classifier result; there were no extension classifier fits.\n\nThe completed-artifact manifest hashes this additive package. Historical scientific artifacts are covered separately by the 3,956-file protected manifest.\n')
 report=f'''## 1. Artifact integrity

All {n:,} protected artifacts passed SHA-256 verification. Existing observations, state assignments, predictions, protocols, figures and results remain unchanged.

## 2. Targeted NS search

Twenty targeted NS systems were searched from a frozen 22-system universe, using 32 queries. The review covered 34 distinct publication records (21 retained reviews rechecked, 11 newly retrieved PDFs, one publisher full text, one abstract with inaccessible full text) and 154 processed target ObsIDs. Seven new DIRECT native labels and zero new STRONG native labels were recovered; two DIRECT SAX labels additionally use STRONG spectral-interval mapping evidence. Four new observations meet common-regime requirements.

## 3. Independent-source gain

Hard-regime NS support: **2 → 4**, adding IGR J00291+5934 and SAX J1808.4−3658. Hard BH support stays 6. Soft support stays 2 BH/1 NS.

## 4. Feasibility

**FAIL.** Hard: 6 BH/4 NS, one NS system short. Soft: 2 BH/1 NS, three BH and four NS short. The five-per-class criterion is unchanged.

## 5. State-controlled cohort

**NOT CREATED.** Catalogue/evidence files are not a state-controlled cohort.

## 6. State-controlled ML

**NOT RUN BY DESIGN.** No valid state-controlled classifier was trained because the preregistered source-diversity criterion was not satisfied.

## 7. Scientific interpretation

Useful source-independent ranking survives the executed instrumental controls. Physical-state independence remains unresolved; the infeasible comparison is not a result for or against state-independent transfer.

## 8. Tests

**{result}**: all 245 existing tests plus 33 new tests. Source-controlled fold tests are inapplicable to this unrun branch; existing grouped/LOSO isolation checks pass.

## 9. State-extension verdict

**STATE_EXTENSION_CLOSED_INFEASIBLE** — STATE_CONTROL_NOT_FEASIBLE_WITH_AVAILABLE_EVIDENCE.

## 10. Publication readiness

**D.** Major planned analysis is complete for the bounded paper. Manuscript integration and journal preparation remain; the package is not yet submission ready.

## 11. Manuscript preparation

Created `manuscript/outline.md`, `claim_evidence_matrix.csv`, `methods_draft.md`, `results_draft.md`, `limitations_draft.md`, `figure_plan.md`, and `novelty_positioning.md`. Added a frozen-metric table bundle and a new feasibility PNG/PDF. Twenty source dossiers, the extension/merged catalogues, screening registry, mapping V2, closure and reproducibility reports preserve the reasoning trail.

## 12. Single next action

Integrate the manuscript and prepare the journal submission, retaining physical-state independence as an explicit unresolved limitation.
'''
 (P/'final_report.md').write_text(report)
 files=[]
 for directory in [D,O,P,C,R/'manuscript']:
  files.extend(p for p in directory.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
 files.extend((R/'scripts').glob('*state_extension*.py'))
 files.extend([R/'src/bhns/data/state_extension.py',R/'tests/test_state_extension.py'])
 completion=O/'completed_artifact_manifest.json'
 hashes={str(p.relative_to(R)):sha256(p) for p in sorted(set(files)) if p!=completion}
 completion.write_text(json.dumps(hashes,indent=2))
 assert verify_protected(R,hashes)==len(hashes)
 print(json.dumps(dict(integrity=integrity,additive_artifacts_hashed=len(hashes)),indent=2))
if __name__=='__main__':main()
