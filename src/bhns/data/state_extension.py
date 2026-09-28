"""Additive state evidence; deliberately contains no model-fitting entry point."""
from datetime import datetime
import pandas as pd
import numpy as np
from astropy.time import Time

LEVELS = {'DIRECT', 'STRONG', 'PROVISIONAL', 'UNRESOLVED', 'CONFLICTED'}
REGIMES = {'HARD_DOMINATED', 'SOFT_DOMINATED', 'UNMAPPED'}
FIELDS = ['rxte_obsid', 'source_id', 'canonical_source', 'class_label',
          'native_state_label', 'common_regime', 'evidence_level', 'evidence_method',
          'reference_id', 'reference_url_or_identifier', 'direct_obsid_match',
          'date_match', 'gti_match', 'whole_observation_supported', 'ambiguous',
          'conflicted', 'eligible_for_confirmatory', 'notes']


def admissible(row):
    return (row['evidence_level'] in {'DIRECT', 'STRONG'}
            and bool(row['whole_observation_supported'])
            and not bool(row['ambiguous']) and not bool(row['conflicted'])
            and row['native_state_label'] not in {'MIXED_OR_TRANSITION', 'UNCLASSIFIED', 'CONFLICTED'}
            and row['common_regime'] in REGIMES - {'UNMAPPED'})


def validate_extension(frame):
    if set(FIELDS) - set(frame):
        raise ValueError('Missing extension schema fields')
    if frame.rxte_obsid.duplicated().any():
        raise ValueError('Duplicate extension ObsID')
    if not set(frame.evidence_level) <= LEVELS or not set(frame.common_regime) <= REGIMES:
        raise ValueError('Invalid evidence level or regime')
    for row in frame.to_dict('records'):
        for field in ['direct_obsid_match', 'date_match', 'gti_match', 'whole_observation_supported',
                      'ambiguous', 'conflicted', 'eligible_for_confirmatory']:
            if not isinstance(row[field], (bool, np.bool_)):
                raise ValueError('Boolean flags must be actual booleans')
        if row['evidence_level'] != 'UNRESOLVED' and not str(row['reference_id']).strip():
            raise ValueError('Unreferenced evidence')
        if row['evidence_level'] == 'DIRECT' and not row['direct_obsid_match']:
            raise ValueError('DIRECT requires exact published ObsID')
        if row['evidence_level'] == 'STRONG' and not row['date_match']:
            raise ValueError('STRONG requires published interval containment')
        if bool(row['eligible_for_confirmatory']) != admissible(row):
            raise ValueError('Eligibility inconsistent with evidence')
        if row['conflicted'] and (not row['ambiguous'] or row['evidence_level'] != 'CONFLICTED'):
            raise ValueError('Conflict must remain excluded and explicit')


def merge_catalogues(original, extension):
    """One analysis row per original ObsID, with every original field retained."""
    validate_extension(extension)
    if original.rxte_obsid.duplicated().any() or not set(extension.rxte_obsid) <= set(original.rxte_obsid):
        raise ValueError('Extension must refer to unique frozen universe ObsIDs')
    byid = extension.set_index('rxte_obsid').to_dict('index')
    rows = []
    for old in original.to_dict('records'):
        row = dict(old)
        row.update({'original_' + k: v for k, v in old.items()})
        row['state_provenance'] = 'original_state_stage'
        row['extension_reviewed'] = old['rxte_obsid'] in byid
        ext = byid.get(old['rxte_obsid'])
        if ext:
            if old['source_id'] != ext['source_id'] or old['class_label'] != ext['class_label']:
                raise ValueError('Source/class identity mismatch')
            row.update({'extension_' + k: v for k, v in ext.items()})
            if ext['evidence_level'] != 'UNRESOLVED':
                conflict = (old['state_confidence'] not in {'UNRESOLVED'}
                            and old['native_state_label'] != ext['native_state_label'])
                if conflict or ext['conflicted']:
                    row.update(native_state_label='CONFLICTED', common_regime='UNMAPPED',
                               state_confidence='CONFLICTED', state_evidence_level='CONFLICTED',
                               ambiguous=True, state_provenance='original_and_extension_conflict')
                elif old['state_confidence'] == 'UNRESOLVED':
                    row.update(native_state_label=ext['native_state_label'], common_regime=ext['common_regime'],
                               state_confidence=ext['evidence_level'], state_evidence_level=ext['evidence_level'],
                               ambiguous=ext['ambiguous'], reference_id=ext['reference_id'],
                               reference_identifier_or_url=ext['reference_url_or_identifier'],
                               notes=ext['notes'], state_assignment_method=ext['evidence_method'],
                               obsid_directly_listed=ext['direct_obsid_match'], date_window_match=ext['date_match'],
                               state_provenance='extension_state_stage')
                    row.update(state_family=('NS_ATOLL' if ext['native_state_label'].startswith('NS_')
                                             else ext['native_state_label']),
                               source_state_taxonomy='Publication-specific native NS state; see extension evidence',
                               reference_title='See extension reference registry: ' + ext['reference_id'],
                               reference_authors='', reference_year='',
                               evidence_time_start=ext.get('evidence_time_start', ''),
                               evidence_time_end=ext.get('evidence_time_end', ''))
                    # The active original-schema columns use ISO dates; preserve
                    # the extension's published numeric MJD in extension_ fields.
                    for key in ['evidence_time_start', 'evidence_time_end']:
                        value = row[key]
                        if isinstance(value, (int, float, np.number)) and np.isfinite(value):
                            row[key] = Time(value, format='mjd', scale='utc').isot
        row['eligible_for_confirmatory'] = (row['state_confidence'] in {'DIRECT', 'STRONG'}
            and not row['ambiguous'] and row['common_regime'] != 'UNMAPPED'
            and row['native_state_label'] != 'MIXED_OR_TRANSITION')
        if row['state_provenance'] == 'extension_state_stage':
            row['eligible_for_confirmatory'] = ext['eligible_for_confirmatory']
        rows.append(row)
    return pd.DataFrame(rows)


def source_gate(frame, minimum=5):
    """Count physical systems, never spectra. A zero-observation class is zero."""
    eligible = frame[frame.eligible_for_confirmatory]
    rows = []
    for regime in sorted(REGIMES - {'UNMAPPED'}):
        g = eligible[eligible.common_regime.eq(regime)]
        row = {'common_regime': regime}
        for cls in ['BH', 'NS']:
            c = g[g.class_label.eq(cls)]
            row[cls + '_sources'] = c.source_id.nunique()
            row[cls + '_observations'] = len(c)
            for level in ['DIRECT', 'STRONG']:
                row[cls + '_' + level + '_sources'] = c[c.state_confidence.eq(level)].source_id.nunique()
        row['PASS'] = min(row['BH_sources'], row['NS_sources']) >= minimum
        rows.append(row)
    return pd.DataFrame(rows)


def validate_chronology(plan, mapping, status):
    if datetime.fromisoformat(plan['frozen_utc']) > datetime.fromisoformat(mapping['frozen_utc']):
        raise ValueError('Mapping precedes search plan')
    if datetime.fromisoformat(mapping['frozen_utc']) > datetime.fromisoformat(status['decided_utc']):
        raise ValueError('Gate precedes frozen mapping')
    if status['branch'] == 'B' and (status['ml_runs'] or status['cohort_created']):
        raise ValueError('Infeasible branch must not fit or construct a confirmatory cohort')
