"""Tests for skills/hill-climb/scripts/aggregate.py (standard library only).

Run from the repo root:  python -m unittest discover -s tests -v
"""
import contextlib
import importlib.util
import io
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / 'skills' / 'hill-climb' / 'scripts' / 'aggregate.py'
EXAMPLE = ROOT / 'examples' / 'landing-page'
spec = importlib.util.spec_from_file_location('aggregate', SCRIPT)
aggregate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aggregate)


class AggregateTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='hill-climb-test-')
        self.addCleanup(temporary.cleanup)
        self.run = Path(temporary.name)
        self.config = {
            'mode': 'climb',
            'judges': [{'name': f'J{i}', 'provider': f'provider{i}'} for i in range(3)],
            'references': ['leader'], 'checks': ['build'],
        }
        self.write('run.json', self.config)
        self.write('rubric.json', ['quality', 'clarity'])
        self.round(0, 'v0')

    def write(self, relative, value):
        path = self.run / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding='utf-8')

    def read(self, relative):
        return json.loads((self.run / relative).read_text(encoding='utf-8'))

    def round(self, index, candidate, incumbent=None, winners=None, score=9.5, labels=None):
        prefix = f'round-{index}'
        self.write(f'{prefix}/round.json', {'candidate': candidate, 'incumbent': incumbent})
        labels = labels or ({'A': 'incumbent', 'B': 'leader', 'C': 'ours'} if incumbent else {'A': 'ours', 'B': 'leader'})
        self.write(f'{prefix}/labels.json', labels)
        self.write(f'{prefix}/checks.json', {'candidate': candidate, 'results': {
            'build': {'passed': True, 'evidence': 'build.log: exit 0'},
        }})
        for index_judge in range(3):
            data = {'judge': f'J{index_judge}', 'items': {label: {'scores': {
                'quality': score if name == 'ours' else 9.0,
                'clarity': score if name == 'ours' else 9.0,
            }} for label, name in labels.items()}}
            if incumbent:
                winner = winners[index_judge] if winners else 'ours'
                label = next((k for k, v in labels.items() if v == winner), 'tie')
                data['comparison'] = {'winner': label, 'reason': 'Specific observed difference.'}
            self.write(f'{prefix}/J{index_judge}.json', data)

    def verdict(self, expected, *flags):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = aggregate.main([str(self.run), *flags])
        self.assertEqual(code, expected, out.getvalue())
        self.assertIn(f'RESULT: { {0: "PASS", 1: "FAIL", 2: "INVALID", 3: "INCOMPLETE"}[expected]}', out.getvalue())
        return out.getvalue()

    def test_example_passes(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = aggregate.main([str(EXAMPLE), '--target', '9'])
        self.assertEqual(code, 0, out.getvalue())
        self.assertIn('RESULT: PASS', out.getvalue())
        self.assertIn('| Gemini Pro | 6.0 | not run | 9.3 |', out.getvalue())

    def test_complete_baseline_passes(self):
        self.assertIn('BEST: v0', self.verdict(0))

    def test_score_mode_without_pair_passes(self):
        self.config['mode'] = 'score'
        self.write('run.json', self.config)
        self.verdict(0)

    def test_legacy_and_missing_rubric_are_incomplete(self):
        for name in ['run.json', 'rubric.json']:
            with self.subTest(name=name):
                saved = self.read(name)
                (self.run / name).unlink()
                self.verdict(3)
                self.write(name, saved)

    def test_only_one_answer_cannot_pass(self):
        for judge in ['J1', 'J2']:
            (self.run / f'round-0/{judge}.json').unlink()
        self.verdict(3)

    def test_declaring_a_single_judge_cannot_bypass_panel(self):
        self.config['judges'] = self.config['judges'][:1]
        self.write('run.json', self.config)
        for judge in ['J1', 'J2']:
            (self.run / f'round-0/{judge}.json').unlink()
        self.verdict(3)

    def test_same_provider_is_degraded(self):
        for judge in self.config['judges']:
            judge['provider'] = 'same'
        self.write('run.json', self.config)
        self.verdict(3)

    def test_advisory_cannot_manufacture_pass(self):
        self.verdict(3, '--advisory', 'J2')

    def test_all_judges_omitting_category_is_incomplete(self):
        for index in range(3):
            path = f'round-0/J{index}.json'
            data = self.read(path)
            del data['items']['A']['scores']['clarity']
            self.write(path, data)
        self.verdict(3)

    def test_missing_reference_score_is_incomplete(self):
        data = self.read('round-0/J0.json')
        del data['items']['B']
        self.write('round-0/J0.json', data)
        self.verdict(3)

    def test_invalid_score_values_are_rejected(self):
        original = self.read('round-0/J0.json')
        for value in [99, 0, -1, math.nan, math.inf, -math.inf, 'NaN', '9.5', True, None, [], {}]:
            with self.subTest(value=value):
                data = json.loads(json.dumps(original))
                data['items']['A']['scores']['quality'] = value
                self.write('round-0/J0.json', data)
                self.verdict(2)

    def test_unknown_category_is_invalid(self):
        data = self.read('round-0/J0.json')
        data['items']['A']['scores']['typo'] = 10
        self.write('round-0/J0.json', data)
        self.verdict(2)

    def test_duplicate_judge_and_duplicate_json_keys_are_invalid(self):
        self.write('round-0/duplicate.json', self.read('round-0/J0.json'))
        self.verdict(2)
        (self.run / 'round-0/duplicate.json').unlink()
        (self.run / 'rubric.json').write_text('{"a": 1, "a": 2}', encoding='utf-8')
        self.verdict(2)

    def test_missing_failed_and_stale_checks_block_pass(self):
        path = 'round-0/checks.json'
        data = self.read(path)
        (self.run / path).unlink()
        self.verdict(3)
        data['results']['build']['passed'] = False
        self.write(path, data)
        self.verdict(1)
        data['candidate'] = 'another-snapshot'
        self.write(path, data)
        self.verdict(2)

    def test_explicit_no_checks_or_references(self):
        self.config.update(checks=[], references=[])
        self.write('run.json', self.config)
        (self.run / 'round-0/checks.json').unlink()
        self.write('round-0/labels.json', {'A': 'ours'})
        for index in range(3):
            path = f'round-0/J{index}.json'
            data = self.read(path)
            del data['items']['B']
            self.write(path, data)
        self.assertIn('no external references', self.verdict(0))

    def test_winning_candidate_is_retained(self):
        self.round(1, 'v1', 'v0', ['ours', 'ours', 'incumbent'])
        self.assertIn('BEST: v1', self.verdict(0))

    def test_losing_or_tied_candidate_cannot_pass_on_high_scores(self):
        for winners in [['incumbent'] * 3, ['tie'] * 3, ['ours', 'incumbent', 'tie']]:
            with self.subTest(winners=winners):
                self.round(1, 'v1', 'v0', winners, score=10)
                self.assertIn('BEST: v0', self.verdict(1))

    def test_selection_is_independent_of_absolute_target(self):
        self.round(1, 'v1', 'v0', score=8)
        out = self.verdict(1)
        self.assertIn('BEST: v1', out)
        self.assertIn('KEEP', out)

    def test_rejected_attempt_does_not_become_next_incumbent(self):
        self.round(1, 'v1', 'v0', ['incumbent'] * 3)
        self.round(2, 'v2', 'v0')
        self.assertIn('BEST: v2', self.verdict(0))
        self.write('round-2/round.json', {'candidate': 'v2', 'incumbent': 'v1'})
        self.verdict(2)

    def test_incumbent_is_not_an_external_reference(self):
        self.round(1, 'v1', 'v0')
        for index in range(3):
            path = f'round-1/J{index}.json'
            data = self.read(path)
            data['items']['A']['scores'] = {'quality': 10, 'clarity': 10}
            self.write(path, data)
        self.verdict(0)

    def test_shuffled_labels_do_not_change_selection(self):
        self.round(1, 'v1', 'v0', labels={'A': 'ours', 'B': 'incumbent', 'C': 'leader'})
        self.assertIn('BEST: v1', self.verdict(0))

    def test_missing_comparison_is_incomplete(self):
        self.round(1, 'v1', 'v0')
        data = self.read('round-1/J0.json')
        del data['comparison']
        self.write('round-1/J0.json', data)
        self.assertIn('BEST: v0', self.verdict(3))

    def test_reference_cannot_win_pairwise_comparison(self):
        self.round(1, 'v1', 'v0')
        data = self.read('round-1/J0.json')
        data['comparison']['winner'] = 'B'
        self.write('round-1/J0.json', data)
        self.verdict(2)

    def test_failed_check_prevents_promotion(self):
        self.round(1, 'v1', 'v0')
        data = self.read('round-1/checks.json')
        data['results']['build']['passed'] = False
        self.write('round-1/checks.json', data)
        self.assertIn('BEST: v0', self.verdict(1))

    def test_invalid_cli_numbers(self):
        for flag, value in [('--target', 'nan'), ('--target', '11'), ('--noise', '-1'), ('--tolerance', 'inf')]:
            with self.subTest(flag=flag, value=value):
                self.verdict(2, flag, value)


if __name__ == '__main__':
    unittest.main()
