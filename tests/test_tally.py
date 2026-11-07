"""Tests for skills/blind-climb/scripts/tally.py (standard library only).

Run from the repo root:  python -m unittest discover -s tests -v
"""

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / 'skills' / 'blind-climb' / 'scripts' / 'tally.py'
spec = importlib.util.spec_from_file_location('tally', SCRIPT)
tally = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tally)


class TallyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='blind-climb-test-')
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        self.config = {
            'reviewers': [{'name': f'R{i}', 'provider': f'provider{i}'} for i in range(3)],
            'checks': ['build'],
        }
        self.write('run.json', self.config)
        self.round(0, 'v0', ready=False, major=True)

    def write(self, relative, value):
        path = self.folder / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding='utf-8')

    def read(self, relative):
        return json.loads((self.folder / relative).read_text(encoding='utf-8'))

    def assessment(self, folder, versions, labels, preferences, ready, major_roles=()):
        self.write(f'{folder}/round.json', {'versions': versions})
        self.write(f'{folder}/labels.json', labels)
        self.write(
            f'{folder}/checks.json',
            {
                'snapshots': {
                    snapshot: {
                        'build': {'passed': True, 'evidence': f'{snapshot}-build.log: exit 0'},
                    }
                    for snapshot in versions.values()
                }
            },
        )
        for index in range(3):
            preference = preferences[index]
            preferred = next((label for label, role in labels.items() if role == preference), preference)
            self.write(
                f'{folder}/R{index}.json',
                {
                    'reviewer': f'R{index}',
                    'preferred': preferred,
                    'why': 'Specific observed reasons for the preference.',
                    'ready_to_ship': {label: ready[role] for label, role in labels.items()},
                    'findings': {
                        label: (
                            [
                                {
                                    'severity': 'major',
                                    'where': 'form',
                                    'problem': 'Submission fails',
                                    'fix': 'Restore submission',
                                }
                            ]
                            if role in major_roles
                            else []
                        )
                        for label, role in labels.items()
                    },
                },
            )

    def round(self, index, current, candidate=None, preferences=None, ready=True, major=False, labels=None):
        versions = {'current': current}
        if candidate:
            versions['candidate'] = candidate
        labels = labels or ({'X': 'candidate', 'Y': 'current'} if candidate else {'X': 'current'})
        readies = {role: ready for role in versions}
        preferences = preferences or (['candidate'] * 3 if candidate else ['current'] * 3)
        self.assessment(f'round-{index}', versions, labels, preferences, readies, versions.keys() if major else ())

    def final(self, final='v1', original='v0', preferences=None, ready=True, major=False, folder='final-check'):
        self.assessment(
            folder,
            {'final': final, 'original': original},
            {'X': 'original', 'Y': 'final'},
            preferences or ['final'] * 3,
            {'final': ready, 'original': False},
            ['final'] if major else (),
        )

    def verdict(self, expected, *flags):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = tally.main([str(self.folder), *flags])
        self.assertEqual(code, expected, output.getvalue())
        status = {0: 'DONE', 1: 'CONTINUE', 2: 'INVALID', 3: 'PLATEAU', 4: 'INCOMPLETE', 5: 'REVIEW_REQUIRED'}[expected]
        self.assertIn(f'RESULT: {status}', output.getvalue())
        return output.getvalue()

    def test_in_progress_review_does_not_need_final_yet(self):
        self.assertIn('REVIEW: CONTINUE', self.verdict(1))

    def test_ready_alone_is_not_done(self):
        self.round(0, 'v0')
        out = self.verdict(4)
        self.assertIn('REVIEW: READY', out)
        self.assertIn('final-check required', out)

    def test_full_review_and_final_check_finish(self):
        self.round(1, 'v0', 'v1')
        self.final()
        out = self.verdict(0)
        self.assertIn('BEST: v1', out)
        self.assertIn('FINAL CHECK: COMPLETE', out)

    def test_missing_manifest_is_incomplete(self):
        (self.folder / 'run.json').unlink()
        self.verdict(4)

    def test_one_reply_or_no_replies_cannot_finish(self):
        self.round(0, 'v0')
        for index in [1, 2]:
            (self.folder / f'round-0/R{index}.json').unlink()
        self.verdict(4)
        (self.folder / 'round-0/R0.json').unlink()
        self.verdict(4)

    def test_single_declared_reviewer_cannot_bypass_panel(self):
        self.config['reviewers'] = self.config['reviewers'][:1]
        self.write('run.json', self.config)
        for index in [1, 2]:
            (self.folder / f'round-0/R{index}.json').unlink()
        self.verdict(4)

    def test_three_reviewers_from_same_provider_are_degraded(self):
        for reviewer in self.config['reviewers']:
            reviewer['provider'] = 'Same Provider'
        self.write('run.json', self.config)
        self.verdict(4)

    def test_all_advisory_never_means_done(self):
        self.round(0, 'v0')
        self.final(final='v0')
        self.verdict(4, '--advisory', 'R0', '--advisory', 'R1', '--advisory', 'R2')

    def test_unknown_advisory_name_is_invalid(self):
        self.verdict(2, '--advisory', 'typo')

    def test_readiness_requires_literal_boolean(self):
        original = self.read('round-0/R0.json')
        for value in ['false', 'true', 1, 0, None, [], {}]:
            with self.subTest(value=value):
                data = json.loads(json.dumps(original))
                data['ready_to_ship']['X'] = value
                self.write('round-0/R0.json', data)
                self.verdict(2)

    def test_readiness_or_findings_omitted_are_incomplete(self):
        original = self.read('round-0/R0.json')
        for field in ['ready_to_ship', 'findings']:
            with self.subTest(field=field):
                data = json.loads(json.dumps(original))
                del data[field]['X']
                self.write('round-0/R0.json', data)
                self.verdict(4)

    def test_major_finding_blocks_done_even_when_ready_is_true(self):
        self.round(0, 'v0', major=True)
        self.final(final='v0')
        self.verdict(1)

    def test_empty_findings_are_valid_and_need_not_be_invented(self):
        self.round(0, 'v0')
        self.final(final='v0', preferences=['tie'] * 3)
        out = self.verdict(0)
        self.assertIn('no improvement is claimed', out)

    def test_bad_or_missing_finding_fields(self):
        original = self.read('round-0/R0.json')
        for field in ['severity', 'where', 'problem', 'fix']:
            with self.subTest(field=field):
                data = json.loads(json.dumps(original))
                del data['findings']['X'][0][field]
                self.write('round-0/R0.json', data)
                self.verdict(4)
        data = json.loads(json.dumps(original))
        data['findings']['X'][0]['severity'] = 'critical'
        self.write('round-0/R0.json', data)
        self.verdict(2)

    def test_duplicate_or_unknown_reviewer_is_invalid(self):
        self.write('round-0/extra.json', self.read('round-0/R0.json'))
        self.verdict(2)
        data = self.read('round-0/extra.json')
        data['reviewer'] = 'unexpected'
        self.write('round-0/extra.json', data)
        self.verdict(2)

    def test_duplicate_json_keys_and_malformed_json_are_invalid(self):
        for raw in ['{"reviewers": [], "reviewers": []}', '{invalid', 'NaN']:
            with self.subTest(raw=raw):
                (self.folder / 'run.json').write_text(raw, encoding='utf-8')
                self.verdict(2)

    def test_invalid_or_duplicated_role_mapping_is_invalid(self):
        for labels in [{'X': []}, {'X': 'current', 'Y': 'current'}, {'Z': 'current'}]:
            with self.subTest(labels=labels):
                self.write('round-0/labels.json', labels)
                self.verdict(2)

    def test_missing_check_file_or_result_is_incomplete(self):
        saved = self.read('round-0/checks.json')
        (self.folder / 'round-0/checks.json').unlink()
        self.verdict(4)
        saved['snapshots']['v0'] = {}
        self.write('round-0/checks.json', saved)
        self.verdict(4)

    def test_missing_check_evidence_or_passed_is_incomplete(self):
        saved = self.read('round-0/checks.json')
        for field in ['passed', 'evidence']:
            with self.subTest(field=field):
                data = json.loads(json.dumps(saved))
                del data['snapshots']['v0']['build'][field]
                self.write('round-0/checks.json', data)
                self.verdict(4)

    def test_check_passed_requires_boolean(self):
        data = self.read('round-0/checks.json')
        data['snapshots']['v0']['build']['passed'] = 'false'
        self.write('round-0/checks.json', data)
        self.verdict(2)

    def test_failed_baseline_can_be_improved(self):
        data = self.read('round-0/checks.json')
        data['snapshots']['v0']['build']['passed'] = False
        self.write('round-0/checks.json', data)
        self.round(1, 'v0', 'v1')
        self.final()
        self.assertIn('BEST: v1', self.verdict(0))

    def test_failed_candidate_cannot_be_promoted(self):
        self.round(1, 'v0', 'v1', ready=False)
        data = self.read('round-1/checks.json')
        data['snapshots']['v1']['build']['passed'] = False
        self.write('round-1/checks.json', data)
        self.assertIn('BEST: v0', self.verdict(1))

    def test_unknown_snapshot_check_is_invalid(self):
        self.write('round-0/checks.json', {'snapshots': {'other': {}}})
        self.verdict(2)

    def test_explicit_no_checks_is_supported(self):
        self.config['checks'] = []
        self.write('run.json', self.config)
        (self.folder / 'round-0/checks.json').unlink()
        self.verdict(1)

    def test_majority_and_shuffled_labels(self):
        self.round(1, 'v0', 'v1', ['candidate', 'current', 'candidate'], labels={'X': 'current', 'Y': 'candidate'})
        self.final()
        self.assertIn('BEST: v1', self.verdict(0))

    def test_tie_retains_current(self):
        self.round(1, 'v0', 'v1', ['candidate', 'current', 'tie'], ready=False)
        self.assertIn('BEST: v0', self.verdict(1))

    def test_partial_round_cannot_promote(self):
        self.round(1, 'v0', 'v1')
        (self.folder / 'round-1/R2.json').unlink()
        self.assertIn('BEST: v0', self.verdict(4))

    def test_snapshot_chain_uses_retained_version_after_rejection(self):
        self.round(1, 'v0', 'v1', ['current'] * 3, ready=False)
        self.round(2, 'v0', 'v2')
        self.final(final='v2')
        self.assertIn('BEST: v2', self.verdict(0))
        self.write('round-2/round.json', {'versions': {'current': 'v1', 'candidate': 'v2'}})
        self.verdict(2)

    def test_reusing_candidate_id_is_invalid(self):
        self.round(1, 'v0', 'v1', ['current'] * 3, ready=False)
        self.round(2, 'v0', 'v1')
        self.verdict(2)

    def test_incomplete_baseline_blocks_promotion(self):
        (self.folder / 'round-0/R2.json').unlink()
        self.round(1, 'v0', 'v1')
        self.assertIn('BEST: v0', self.verdict(4))

    def test_final_check_needs_full_panel_and_all_findings(self):
        self.round(1, 'v0', 'v1')
        self.final()
        (self.folder / 'final-check/R2.json').unlink()
        self.verdict(4)
        self.final()
        data = self.read('final-check/R0.json')
        del data['findings']['Y']
        self.write('final-check/R0.json', data)
        self.verdict(4)

    def test_stale_final_snapshot_is_invalid(self):
        self.round(1, 'v0', 'v1')
        self.final(final='old-version')
        self.verdict(2)

    def test_failed_final_check_does_not_block_the_next_round(self):
        self.round(1, 'v0', 'v1')
        self.final(major=True)
        self.verdict(1)
        self.round(2, 'v1', 'v2')
        out = self.verdict(4)
        self.assertIn('checked an earlier snapshot', out)
        self.assertIn('final-check required', out)
        self.final(final='v2', folder='final-check-2')
        self.assertIn('BEST: v2', self.verdict(0))

    def test_rejected_candidate_keeps_the_final_check_valid(self):
        self.round(1, 'v0', 'v1')
        self.final()
        self.round(2, 'v1', 'v2', ['current'] * 3)
        self.assertIn('BEST: v1', self.verdict(0))

    def test_latest_final_check_is_chosen_by_number(self):
        self.round(1, 'v0', 'v1')
        self.round(2, 'v1', 'v2')
        self.final(final='v2', folder='final-check-2', major=True)
        self.final(final='v2', folder='final-check-10')
        self.verdict(0)

    def test_advisory_only_affects_the_latest_round(self):
        self.round(1, 'v0', 'v1', ready=False)
        self.round(2, 'v1', 'v2', ready=False)
        out = self.verdict(4, '--advisory', 'R2')
        self.assertIn('BEST: v1', out)
        self.assertRegex(out, r'round-1 .*KEEP')
        self.assertRegex(out, r'round-2 .*INCOMPLETE')

    def test_advisory_on_a_final_check_leaves_the_rounds_alone(self):
        self.round(1, 'v0', 'v1')
        self.final()
        out = self.verdict(4, '--advisory', 'R2')
        self.assertIn('BEST: v1', out)
        self.assertRegex(out, r'round-1 .*KEEP')
        self.assertIn('FINAL CHECK: INCOMPLETE', out)

    def test_wrong_original_snapshot_is_invalid(self):
        self.round(1, 'v0', 'v1')
        self.final(original='not-original')
        self.verdict(2)

    def test_final_loses_or_ties_requires_human_review(self):
        self.round(1, 'v0', 'v1')
        for preferences in [['original'] * 3, ['tie'] * 3, ['final', 'original', 'tie']]:
            with self.subTest(preferences=preferences):
                self.final(preferences=preferences)
                self.verdict(5)

    def test_major_or_not_ready_in_final_blocks_done(self):
        self.round(1, 'v0', 'v1')
        self.final(major=True)
        self.verdict(1)
        self.final(ready=False)
        self.verdict(1)

    def test_failed_final_checks_block_done(self):
        self.round(1, 'v0', 'v1')
        self.final()
        data = self.read('final-check/checks.json')
        data['snapshots']['v1']['build']['passed'] = False
        self.write('final-check/checks.json', data)
        self.verdict(1)

    def test_plateau_needs_final_check(self):
        self.round(1, 'v0', 'v1', ['current'] * 3, ready=False)
        self.round(2, 'v0', 'v2', ['current'] * 3, ready=False)
        out = self.verdict(4)
        self.assertIn('REVIEW: PLATEAU', out)
        self.final(final='v0', ready=False)
        self.verdict(3)

    def test_ready_retained_version_takes_priority_over_plateau(self):
        self.round(0, 'v0')
        self.round(1, 'v0', 'v1', ['current'] * 3)
        self.round(2, 'v0', 'v2', ['current'] * 3)
        self.final(final='v0')
        self.verdict(0)

    def test_budget_finalization_requires_final_check(self):
        self.verdict(4, '--finalize')
        self.final(final='v0', ready=False, major=True)
        self.verdict(1, '--finalize')


if __name__ == '__main__':
    unittest.main()
