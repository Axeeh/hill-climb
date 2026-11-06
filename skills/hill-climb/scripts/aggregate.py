#!/usr/bin/env python3
"""Aggregate a declared jury and blind comparisons. See references/run-format.md.
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
    if any(not isinstance(v, str) for v in labels.values()) or set(labels.values()) != expected_items or len(labels) != len(expected_items):
        raise ValueError('labels.json must map each required item exactly once')
    missing, failed, judges = [], [], {}
    reserved = {'round.json', 'labels.json', 'checks.json'}
    for path in sorted(folder.glob('*.json')):
        if path.name in reserved:
            continue
        data = obj(read_json(path), str(path))
        judge = text_value(data.get('judge'), f'{path}: judge')
        if judge not in roster or judge in judges:
            raise ValueError(f'{path}: unknown or duplicate judge {judge}')
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
            pair = data.get('comparison')
            if pair is None:
                missing.append(f'{judge}: missing blind comparison')
            else:
                obj(pair, 'comparison')
                winner_label = text_value(pair.get('winner'), 'comparison.winner')
                pair_labels = {key for key, value in labels.items() if value in ('ours', 'incumbent')}
                if winner_label != 'tie' and winner_label not in pair_labels:
                    raise ValueError(f'{judge}: winner must be a candidate/incumbent label or tie')
                text_value(pair.get('reason'), 'comparison.reason')
                winner = 'tie' if winner_label == 'tie' else labels[winner_label]
        judges[judge] = {'scores': scores, 'winner': winner}
    for judge in roster.keys() - judges.keys():
        missing.append(f'{judge}: not run')
    checks_path = folder / 'checks.json'
    if checks_path.exists():
        record = obj(read_json(checks_path), 'checks.json')
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
    elif checks:
        missing.append('missing checks.json')
    return {'folder': folder.name, 'candidate': candidate, 'incumbent': incumbent,
            'judges': judges, 'missing': missing, 'failed': failed}

def judge_min(row, judge):
    scores = row['judges'].get(judge, {}).get('scores', {}).get('ours', {})
    return min(scores.values()) if scores else None

def fmt(value):
    return 'n/a' if value is None else f'{value:.1f}'

def run(args):
    mode, categories, roster, references, checks = load_config(Path(args.run))
    if set(args.advisory) - roster.keys():
        raise ValueError('unknown advisory judge')
    folders = sorted((p for p in Path(args.run).iterdir() if p.is_dir() and re.fullmatch(r'round-\d+', p.name)),
                     key=lambda p: int(p.name.split('-')[1]))
    if not folders:
        raise Incomplete('no round-N folders')
    if [p.name for p in folders] != [f'round-{i}' for i in range(len(folders))]:
        raise ValueError('rounds must start at round-0 and be consecutive')
    if mode == 'score' and len(folders) != 1:
        raise ValueError('Score mode has exactly one round')
    panel_missing = []
    if len(roster) < 3 or len(set(roster.values())) < 3:
        panel_missing.append('full council requires at least three judges from three distinct providers')
    if args.advisory:
        panel_missing.append('required judges marked advisory: ' + ', '.join(args.advisory))
    active = [j for j in roster if j not in args.advisory]
    rows, best, seen = [], None, set()
    print('## Blind selection\n')
    print('| Round | Candidate | Incumbent | Candidate / incumbent / tie votes | Selection |')
    print('|---|---|---|---|---|')
    for index, folder in enumerate(folders):
        row = load_round(folder, categories, roster, references, checks, mode == 'climb' and index > 0)
        if row['candidate'] in seen:
            raise ValueError('candidate snapshot IDs must be unique; each round is immutable')
        seen.add(row['candidate'])
        if index and row['incumbent'] != best:
            raise ValueError(f'{folder.name}: incumbent must be the best retained snapshot ({best})')
        row['missing'].extend(panel_missing)
        votes = Counter(row['judges'][j]['winner'] for j in active if j in row['judges'])
        complete = not row['missing']
        row['accepted'] = complete and not row['failed'] and (index == 0 or votes['ours'] > len(roster) / 2)
        if row['accepted']:
            best = row['candidate']
        row['best'] = best
        selection = 'KEEP' if row['accepted'] else ('INCOMPLETE' if not complete else 'REJECT')
        row['selection'] = selection
        print(f"| {folder.name} | {row['candidate']} | {row['incumbent'] or '—'} | "
              f"{votes['ours']} / {votes['incumbent']} / {votes['tie']} | {selection} |")
        rows.append(row)
    print('\n## Minimum score per round (ours)\n')
    print('| Judge | ' + ' | '.join(r['folder'] for r in rows) + ' |')
    print('|---|' + '---|' * len(rows))
    for judge in roster:
        print(f'| {judge}' + (' (advisory)' if judge in args.advisory else '') + ' | ' + ' | '.join(
            'not run' if judge_min(r, judge) is None else fmt(judge_min(r, judge)) for r in rows) + ' |')
    final = rows[-1]
    reasons = list(final['failed'])
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
    # Historical score comparisons remain diagnostic; blind voting selects the retained version.
    if len(rows) >= 2:
        for judge in active:
            before, now = judge_min(rows[-2], judge), judge_min(final, judge)
            if before is not None and now is not None and before - now >= args.noise:
                print(f'REGRESSION: {judge} minimum {before:.1f} → {now:.1f}; inspect the blind comparison.')
    if len(rows) >= 3:
        series = [[judge_min(r, j) for r in rows[-3:]] for j in active]
        series = [s for s in series if None not in s]
        if series and all(s[2] - s[1] < args.plateau and s[1] - s[0] < args.plateau for s in series):
            print('WARNING: plateau over two rounds.')
    if not references:
        print('WARNING: no external references declared; absolute scores only.')
    print(f"\nBEST: {best or 'none validated'}")
    if final['missing']:
        status, code, messages = 'INCOMPLETE', 3, final['missing'] + reasons
    else:
        if not final['accepted']:
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
    parser.add_argument('run')
    parser.add_argument('--target', type=float, default=9.0)
    parser.add_argument('--advisory', action='append', default=[])
    parser.add_argument('--tolerance', type=float, default=0.0)
    parser.add_argument('--plateau', type=float, default=0.3)
    parser.add_argument('--noise', type=float, default=0.5)
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
