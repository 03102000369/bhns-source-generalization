# Final pre-push report

Local manifest repair completed on 2026-09-25. This replaces the earlier curation status in the same canonical report.

## Merge repair

No merge was in progress at initial inspection: main was `b2ff44ac8762c5866ee2f34ebb03f173da070815`, with two untracked manifest files; Phase II was `6f12ea3b78b483ffbd8e2062f2c9685d219d3454`. There were no unresolved paths, so no abort was needed. After repairing main, a fresh normal merge into phase2-nustar was completed. Only the detached checksum conflicted; the Phase-II version was retained temporarily, then both controls were regenerated before verification and commit. No history was rewritten.

## Release manifests

Both `RELEASE_MANIFEST.csv` and `RELEASE_MANIFEST.sha256` are tracked and retained. The official generator, `scripts/update_release_manifest.py`, regenerated each pair from its own final branch tree. `scripts/verify_release.py` passes independently on main (**326 payload files**) and phase2-nustar (**389 payload files**), including exact tracked-file coverage, copied-source hashes and cohort contracts. Including the two control files, the branches contain 328 and 391 tracked files respectively.

The manifests and their checksums intentionally differ. Phase II has 63 additional active files; its manifest was never replaced with main's as a final resolution. Regeneration and verification were repeated after updating this report. No hashes were edited manually.

## Documentation files

- **`docs/release_provenance.csv`: kept on both branches.** The verifier reads it unconditionally, the generator uses it, and release/gate documentation references it. Main's original 295-row map was restored exactly; Phase II retains its exact 355-row map.
- **`docs/validation_record.md`: kept on both branches.** The Phase-II gate report explicitly directs readers to this historical release-validation evidence. Main's original record was restored, and Phase II retains its additional validation paragraph.
- **`manuscript/AUTHOR_TODOS.md`: restored unchanged.** It is a required hashed entry in the provenance map and is referenced by the manuscript README. Other intentional documentation removals remain. README/CFF links now point to this existing checklist instead of deleted metadata notes.

## Tests

| Branch | Actual lightweight suite | Release integrity | CFF 1.2.0 schema | Manuscript and supplement |
|---|---|---|---|---|
| main | **221 passed, 1 deliberately deselected** (15.20 s) | PASS | PASS | PASS |
| phase2-nustar | **280 passed, 1 deliberately deselected** (14.63 s) | PASS | PASS | PASS |

Established commands: `python -m pytest tests -q` and `python -m pytest tests cross_mission/tests -q`, with plugin autoload disabled, no cache provider, and branch-specific basetemps/JUnit logs under ignored `build/`. The omitted test requires historical full-workspace artifacts. Both TeX builds have no undefined references/citations or overfull boxes. Author TODOs remain; schema validity is not publication-ready authorship metadata.

## Scientific integrity

Every scientific subtree, including all code/scripts, configurations, cohorts, source/ObsID inventories, predictions, metrics, figures, manuscript sources and tests, matches its pre-cleanup state: main compared with `7c77e05648fee08b45719c7ae72ae35276f0afaa`, Phase II with `6f12ea3b78b483ffbd8e2062f2c9685d219d3454`. The restored author checklist matches its original bytes. No scientific data/results changed, and no scientific classifier, reduction or experiment was rerun.

All 64 Phase-II files remain unchanged. Gates remain **X0 PASS; X1 PASS; X2 NOT PASSED; X3–X7 NOT RUN; Cross-mission classification NOT YET TESTED**. Main retains only its existing cross-mission overview.

## Tag integrity

`v1.0.0-phase1-paper` remains attached to **`64afc0407e4d1ffa512c3466c1a8abd2fff7c6f4`**. Annotated tag object **`9d643b2a705c9f13c341f05bb5319aed84903116`** is also unchanged. No retagging occurred.

## Final branches

| Branch | Validated repair/merge commit |
|---|---|
| main | `1aae60d64148d2557b28136c9314ec4420671f13` |
| phase2-nustar | `af739f050306ea4286efe4948e0749e3f6c20605` |

Final tips add only this report and regenerated manifest controls. A tracked report cannot contain its own commit hash; exact final tip hashes are supplied in the task's final handoff and can be obtained with `git rev-parse main phase2-nustar`. Both branches are checked clean after those commits; the final checkout is main.

## Push readiness

**READY_TO_PUSH.** Local repair and validation are complete. Nothing was pushed; no authentication, repository creation, remote change or force operation occurred. Existing origin and local remote-tracking refs remain unchanged. Author metadata/licensing decisions remain pending for publication. Review this report before running the normal push commands provided in the final handoff.
