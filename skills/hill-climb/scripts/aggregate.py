#!/usr/bin/env python3
"""Aggregate a declared jury and its blind rankings. See references/run-format.md.
Exit codes: 0 PASS, 1 FAIL, 2 INVALID, 3 INCOMPLETE.
"""

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path


class Incomplete(ValueError):
    pass


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate JSON key: {key}')
        result[key] = value
    return result


def read_json(path):
    if not path.is_file():
        raise Incomplete(f'missing {path}')
    try:
        return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique_object)
    except (ValueError, UnicodeError) as error:
        raise ValueError(f'{path}: {error}') from error


def obj(value, context):
    if not isinstance(value, dict):
        raise ValueError(f'{context}: expected an object')
    return value


def text_value(value, context):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{context}: expected a non-empty string')
    return value


def names(value, context, allow_empty=False):
    if not isinstance(value, list) or (not value and not allow_empty):
        raise ValueError(f'{context}: expected a list' + ('' if allow_empty else ' with at least one entry'))
    for entry in value:
        text_value(entry, context)
    if len(set(value)) != len(value):
        raise ValueError(f'{context}: duplicate entries')
    return value


def number(value, context, low, high):
    if type(value) not in (int, float) or not low <= value <= high or not math.isfinite(value):
        raise ValueError(f'{context}: expected a finite number between {low} and {high}')
    return float(value)


def load_config(run):
    config = obj(read_json(run / 'run.json'), 'run.json')
    if config.get('mode') not in ('score', 'climb'):
        raise ValueError('run.json: mode must be score or climb')
    categories = names(read_json(run / 'rubric.json'), 'rubric.json')
    judges = config.get('judges')
    if not isinstance(judges, list) or not judges:
        raise ValueError('run.json: judges must be a non-empty list')
    roster = {}
    for judge in judges:
        obj(judge, 'judge')
        name = text_value(judge.get('name'), 'judge.name')
        provider = text_value(judge.get('provider'), 'judge.provider').strip().casefold()
        if name in roster:
            raise ValueError(f'duplicate judge: {name}')
        roster[name] = provider
    references = names(config.get('references'), 'references', allow_empty=True)
    if set(references) & {'ours', 'incumbent'}:
        raise ValueError('references cannot use reserved names ours or incumbent')
    checks = names(config.get('checks'), 'checks', allow_empty=True)
    return config['mode'], categories, roster, references, checks


def parse_ranking(ranking, labels, judge):
    """Return which of the two versions a judge's ranking prefers: ours, incumbent or tie."""
    obj(ranking, f'{judge}: ranking')
    text_value(ranking.get('reason'), f'{judge}: ranking.reason')
    order = ranking.get('order')
    if not isinstance(order, list) or not order:
        raise ValueError(f'{judge}: ranking.order must be a non-empty list of groups')
    positions = {}
    for position, group in enumerate(order):
        if not isinstance(group, list) or not group:
            raise ValueError(f'{judge}: every ranking group must be a non-empty list of labels')
        for label in group:
            if not isinstance(label, str) or label not in labels or label in positions:
                raise ValueError(f'{judge}: unknown or repeated label in ranking: {label}')
            positions[label] = position
    if set(positions) != set(labels):
        return None
    rank = {item: positions[label] for label, item in labels.items()}
    if rank['ours'] == rank['incumbent']:
        return 'tie'
    return 'ours' if rank['ours'] < rank['incumbent'] else 'incumbent'


def parse_answer(path, labels, categories, needs_pair, missing):
    data = obj(read_json(path), str(path))
    judge = text_value(data.get('judge'), f'{path}: judge')
    items = obj(data.get('items'), f'{path}: items')
    if set(items) - set(labels):
        raise ValueError(f'{path}: unknown item label')
    scores = {}
    for label, item in items.items():
        raw = obj(obj(item, label).get('scores'), f'{path}/{label}/scores')
        if set(raw) - set(categories):
            raise ValueError(f'{path}: categories outside rubric.json')
        scores[labels[label]] = {c: number(v, f'{path}/{label}/{c}', 1, 10) for c, v in raw.items()}
    for label, item in labels.items():
        for category in categories:
            if category not in scores.get(item, {}):
                missing.append(f'{judge}: missing {label}/{category}')
    winner = None
    if needs_pair:
        if data.get('ranking') is None:
            missing.append(f'{judge}: missing ranking')
        else:
            winner = parse_ranking(data['ranking'], labels, judge)
            if winner is None:
                missing.append(f'{judge}: ranking does not list every item')
    return judge, {'scores': scores, 'winner': winner}


def parse_checks(folder, candidate, checks, missing, failed):
    path = folder / 'checks.json'
    if not path.exists():
        if checks:
            missing.append('missing checks.json')
        return
    record = obj(read_json(path), 'checks.json')
    if record.get('candidate') != candidate:
        raise ValueError('checks.json belongs to a different candidate snapshot')
    results = obj(record.get('results'), 'checks.results')
    if set(results) - set(checks):
        raise ValueError('checks.json: unknown check')
    for name in checks:
        if name not in results:
            missing.append(f'check not run: {name}')
            continue
        result = obj(results[name], name)
        if type(result.get('passed')) is not bool:
            raise ValueError(f'{name}: passed must be a boolean')
        text_value(result.get('evidence'), f'{name}.evidence')
        if not result['passed']:
            failed.append(f'check failed: {name}')


def load_round(folder, categories, roster, references, checks, needs_pair):
    meta = obj(read_json(folder / 'round.json'), f'{folder.name}/round.json')
    candidate = text_value(meta.get('candidate'), 'round.candidate')
    incumbent = meta.get('incumbent')
    if needs_pair:
        text_value(incumbent, 'round.incumbent')
        if candidate == incumbent:
            raise ValueError('candidate and incumbent snapshot IDs must differ')
    elif incumbent is not None:
        raise ValueError('baseline/score round must have a null incumbent')
    labels = obj(read_json(folder / 'labels.json'), 'labels.json')
    if not labels or any(not re.fullmatch(r'[A-Z]+', key) for key in labels):
        raise ValueError('labels.json: labels must contain uppercase letters only')
    expected_items = {'ours', *references} | ({'incumbent'} if needs_pair else set())
    if (
        any(not isinstance(v, str) for v in labels.values())
        or set(labels.values()) != expected_items
        or len(labels) != len(expected_items)
    ):
        raise ValueError('labels.json must map each required item exactly once')
    missing, failed, judges = [], [], {}
    for path in sorted(folder.glob('*.json')):
        if path.name in {'round.json', 'labels.json', 'checks.json'}:
            continue
        judge, answer = parse_answer(path, labels, categories, needs_pair, missing)
        if judge not in roster or judge in judges:
            raise ValueError(f'{path}: unknown or duplicate judge {judge}')
        judges[judge] = answer
    missing.extend(f'{judge}: not run' for judge in roster if judge not in judges)
    parse_checks(folder, candidate, checks, missing, failed)
    return {
        'folder': folder.name,
        'candidate': candidate,
        'incumbent': incumbent,
        'judges': judges,
        'missing': missing,
        'failed': failed,
    }


def round_folders(run):
    folders = sorted(
        (p for p in run.iterdir() if p.is_dir() and re.fullmatch(r'round-\d+', p.name)),
        key=lambda p: int(p.name.split('-')[1]),
    )
    if not folders:
        raise Incomplete('no round-N folders')
    if [p.name for p in folders] != [f'round-{i}' for i in range(len(folders))]:
        raise ValueError('rounds must start at round-0 and be consecutive')
    return folders


def decide_rounds(folders, mode, categories, roster, references, checks, advisory):
    """Load the rounds in order and decide which snapshot each one retains.

    Round 0 is the starting point, so it is retained even if it fails a check. A
    --advisory judge only affects the latest round: earlier decisions stand.
    """
    panel_missing = []
    if len(roster) < 3 or len(set(roster.values())) < 3:
        panel_missing.append('full council requires at least three judges from three distinct providers')
    rows, best, seen, baseline_missing = [], None, set(), []
    for index, folder in enumerate(folders):
        row = load_round(folder, categories, roster, references, checks, mode == 'climb' and index > 0)
        if row['candidate'] in seen:
            raise ValueError('candidate snapshot IDs must be unique; each round is immutable')
        seen.add(row['candidate'])
        if index and row['incumbent'] != best:
            raise ValueError(f'{folder.name}: incumbent must be the best retained snapshot ({best})')
        if index == 0:
            baseline_missing = list(row['missing'])
        else:
            row['missing'].extend(baseline_missing)
        row['missing'].extend(panel_missing)
        latest = index == len(folders) - 1
        if latest and advisory:
            row['missing'].append('required judges marked advisory: ' + ', '.join(advisory))
        voters = [j for j in roster if not (latest and j in advisory)]
        row['votes'] = Counter(row['judges'][j]['winner'] for j in voters if j in row['judges'])
        complete = not row['missing']
        row['accepted'] = complete and not row['failed'] and (index == 0 or row['votes']['ours'] > len(roster) / 2)
        if index == 0:
            best = row['candidate']
            row['selection'] = 'BASELINE' if complete else 'INCOMPLETE'
        else:
            if row['accepted']:
                best = row['candidate']
            row['selection'] = 'KEEP' if row['accepted'] else ('REJECT' if complete else 'INCOMPLETE')
        rows.append(row)
    return rows, best


def judge_min(row, judge):
    scores = row['judges'].get(judge, {}).get('scores', {}).get('ours', {})
    return min(scores.values()) if scores else None


def judge_history(rows, judge):
    """The judge's minimum per round, skipping the rounds it did not run in."""
    return [value for value in (judge_min(row, judge) for row in rows) if value is not None]


def fmt(value):
    return 'n/a' if value is None else f'{value:.1f}'


def print_selection(rows):
    print('## Blind selection\n')
    print('| Round | Candidate | Incumbent | Candidate / incumbent / tie votes | Selection |')
    print('|---|---|---|---|---|')
    for row in rows:
        votes = row['votes']
        print(
            f'| {row["folder"]} | {row["candidate"]} | {row["incumbent"] or "—"} | '
            f'{votes["ours"]} / {votes["incumbent"]} / {votes["tie"]} | {row["selection"]} |'
        )


def print_minimums(rows, roster, advisory):
    print('\n## Minimum score per round (ours)\n')
    print('| Judge | ' + ' | '.join(r['folder'] for r in rows) + ' |')
    print('|---|' + '---|' * len(rows))
    for judge in roster:
        cells = ['not run' if judge_min(r, judge) is None else fmt(judge_min(r, judge)) for r in rows]
        name = judge + (' (advisory)' if judge in advisory else '')
        print(f'| {name} | ' + ' | '.join(cells) + ' |')


def print_final_categories(final, active, categories, references, args):
    """Print the final table and return why the candidate misses the target."""
    reasons = []
    print('\n## Final categories\n')
    print('| Judge | Category | Candidate | Best external reference | Gap |')
    print('|---|---|---|---|---|')
    for judge in active:
        scores = final['judges'].get(judge, {}).get('scores', {})
        for category in categories:
            ours = scores.get('ours', {}).get(category)
            refs = [scores.get(ref, {}).get(category) for ref in references]
            refs = [v for v in refs if v is not None]
            ref = max(refs) if refs else None
            gap = ours - ref if ours is not None and ref is not None else None
            print(f'| {judge} | {category} | {fmt(ours)} | {fmt(ref)} | {fmt(gap)} |')
            if ours is not None and ours < args.target:
                reasons.append(f'{judge}: {category} below target')
            if gap is not None and gap < -args.tolerance:
                reasons.append(f'{judge}: {category} below best external reference')
    return reasons


def print_warnings(rows, active, references, args):
    """Score history is only a diagnostic: the blind ranking selects the retained version."""
    final = rows[-1]
    histories = [judge_history(rows, j) for j in active if judge_min(final, j) is not None]
    for judge in active:
        history = judge_history(rows, judge)
        if judge_min(final, judge) is not None and len(history) >= 2 and history[-2] - history[-1] >= args.noise:
            print(f'REGRESSION: {judge} minimum {history[-2]:.1f} → {history[-1]:.1f}; inspect the blind ranking.')
    series = [h[-3:] for h in histories if len(h) >= 3]
    if series and all(s[2] - s[1] < args.plateau and s[1] - s[0] < args.plateau for s in series):
        print('WARNING: plateau over two rounds.')
    if not references:
        print('WARNING: no external references declared; absolute scores only.')


def run(args):
    run_dir = Path(args.run)
    mode, categories, roster, references, checks = load_config(run_dir)
    if set(args.advisory) - roster.keys():
        raise ValueError('unknown advisory judge')
    folders = round_folders(run_dir)
    if mode == 'score' and len(folders) != 1:
        raise ValueError('Score mode has exactly one round')
    rows, best = decide_rounds(folders, mode, categories, roster, references, checks, args.advisory)
    active = [j for j in roster if j not in args.advisory]
    final = rows[-1]
    print_selection(rows)
    print_minimums(rows, roster, args.advisory)
    reasons = list(final['failed']) + print_final_categories(final, active, categories, references, args)
    print_warnings(rows, active, references, args)
    print(f'\nBEST: {best}')
    if final['missing']:
        status, code, messages = 'INCOMPLETE', 3, final['missing'] + reasons
    else:
        if not final['accepted'] and len(rows) > 1:
            reasons.append('candidate not retained; restore the best snapshot (ties retain the incumbent)')
        status, code, messages = ('FAIL', 1, reasons) if reasons else ('PASS', 0, [])
    print(f'RESULT: {status}')
    for message in dict.fromkeys(messages):
        print(f'- {message}')
    return code


def main(argv=None):
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', help='the run folder')
    parser.add_argument('--target', type=float, default=9.0, help='score every judge must reach (default: 9)')
    parser.add_argument(
        '--advisory',
        action='append',
        default=[],
        help='judge whose latest answer cites things that are not there; keeps the result INCOMPLETE (repeatable)',
    )
    parser.add_argument(
        '--tolerance', type=float, default=0.0, help='how far below the best reference still passes (default: 0)'
    )
    parser.add_argument(
        '--plateau', type=float, default=0.3, help='minimum rise per round that is not a plateau (default: 0.3)'
    )
    parser.add_argument('--noise', type=float, default=0.5, help='drop reported as a regression (default: 0.5)')
    args = parser.parse_args(argv)
    try:
        number(args.target, 'target', 1, 10)
        number(args.tolerance, 'tolerance', 0, 9)
        number(args.plateau, 'plateau', 0.000001, 9)
        number(args.noise, 'noise', 0.000001, 9)
        return run(args)
    except Incomplete as error:
        print(f'RESULT: INCOMPLETE\n- {error}')
        return 3
    except (ValueError, OSError) as error:
        print(f'RESULT: INVALID\n- {error}')
        return 2


if __name__ == '__main__':
    sys.exit(main())
