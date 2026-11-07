#!/usr/bin/env python3
"""Tally blind-climb reviews. Data contract: references/run-format.md.
Exit: 0 DONE, 1 CONTINUE, 2 INVALID, 3 PLATEAU, 4 INCOMPLETE,
5 REVIEW_REQUIRED (the final version did not win the final check).
"""

import argparse
import json
import re
import sys
from pathlib import Path

SEVERITIES = {'major', 'minor', 'nit'}


class Incomplete(ValueError):
    pass


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate JSON key: {key}')
        result[key] = value
    return result


def invalid_constant(value):
    raise ValueError(f'invalid JSON constant: {value}')


def read_json(path):
    if not path.is_file():
        raise Incomplete(f'missing {path}')
    try:
        return json.loads(
            path.read_text(encoding='utf-8'), object_pairs_hook=unique_object, parse_constant=invalid_constant
        )
    except (ValueError, UnicodeError) as error:
        raise ValueError(f'{path}: {error}') from error


def obj(value, context):
    if not isinstance(value, dict):
        raise ValueError(f'{context}: expected an object')
    return value


def string(value, context):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{context}: expected a non-empty string')
    return value


def string_list(value, context):
    if not isinstance(value, list):
        raise ValueError(f'{context}: expected a list (explicit [] is allowed)')
    for entry in value:
        string(entry, context)
    if len(set(value)) != len(value):
        raise ValueError(f'{context}: duplicate entries')
    return value


def config(run):
    data = obj(read_json(run / 'run.json'), 'run.json')
    entries = data.get('reviewers')
    if not isinstance(entries, list) or not entries:
        raise ValueError('run.json: reviewers must be a non-empty list')
    roster = {}
    for entry in entries:
        obj(entry, 'reviewer')
        name = string(entry.get('name'), 'reviewer.name')
        provider = string(entry.get('provider'), 'reviewer.provider').strip().casefold()
        if name in roster:
            raise ValueError(f'duplicate reviewer: {name}')
        roster[name] = provider
    return roster, string_list(data.get('checks'), 'checks')


def parse_findings(items, name, label, missing):
    if not isinstance(items, list):
        raise ValueError(f'{name}: findings.{label} must be a list')
    for item in items:
        obj(item, 'finding')
        if 'severity' not in item:
            missing.append(f'{name}: missing finding.severity')
            continue
        severity = string(item.get('severity'), 'severity')
        if severity not in SEVERITIES:
            raise ValueError(f'{name}: invalid finding severity')
        for field in ('where', 'problem', 'fix'):
            if field not in item:
                missing.append(f'{name}: missing finding.{field}')
            else:
                string(item[field], f'finding.{field}')
    return items


def parse_answer(path, labels, roles, missing):
    data = obj(read_json(path), str(path))
    name = string(data.get('reviewer'), 'reviewer')
    preference = data.get('preferred')
    if preference is None and len(labels) == 1:
        preferred = next(iter(roles))
    elif preference is None:
        preferred = None
        missing.append(f'{name}: missing preferred version')
    else:
        string(preference, 'preferred')
        if preference != 'tie' and preference not in labels:
            raise ValueError(f'{name}: preferred must be X, Y or tie')
        if len(labels) == 1 and preference == 'tie':
            raise ValueError('a baseline cannot have a tied preference')
        preferred = 'tie' if preference == 'tie' else labels[preference]
    if 'why' not in data:
        missing.append(f'{name}: missing review rationale')
    else:
        string(data['why'], 'why')
    ready_raw = obj(data.get('ready_to_ship', {}), 'ready_to_ship')
    findings_raw = obj(data.get('findings', {}), 'findings')
    if (set(ready_raw) | set(findings_raw)) - set(labels):
        raise ValueError(f'{name}: unknown label in readiness or findings')
    ready, findings = {}, {}
    for label, role in labels.items():
        if label not in ready_raw:
            missing.append(f'{name}: missing ready_to_ship.{label}')
        elif type(ready_raw[label]) is not bool:
            raise ValueError(f'{name}: ready_to_ship.{label} must be a literal boolean')
        else:
            ready[role] = ready_raw[label]
        if label not in findings_raw:
            missing.append(f'{name}: missing findings.{label}; use [] for no findings')
        else:
            findings[role] = parse_findings(findings_raw[label], name, label, missing)
    return name, {'preferred': preferred, 'ready': ready, 'findings': findings}


def parse_checks(folder, versions, required_checks, missing):
    check_failures = {role: [] for role in versions}
    if not (folder / 'checks.json').exists():
        if required_checks:
            missing.append(f'{folder.name}: missing checks.json')
        return check_failures
    snapshots = obj(obj(read_json(folder / 'checks.json'), 'checks.json').get('snapshots'), 'checks.snapshots')
    if set(snapshots) - set(versions.values()):
        raise ValueError(f'{folder.name}: checks belong to an unreviewed snapshot')
    for role, snapshot in versions.items():
        if snapshot not in snapshots:
            missing.append(f'missing checks for snapshot {snapshot}')
            continue
        results = obj(snapshots[snapshot], f'checks.{snapshot}')
        if set(results) - set(required_checks):
            raise ValueError(f'{snapshot}: unknown check')
        for check in required_checks:
            if check not in results:
                missing.append(f'{snapshot}: check not run: {check}')
                continue
            result = obj(results[check], f'{snapshot}/{check}')
            if 'passed' not in result:
                missing.append(f'{snapshot}/{check}: missing passed result')
            elif type(result['passed']) is not bool:
                raise ValueError(f'{snapshot}/{check}: passed must be a literal boolean')
            if 'evidence' not in result:
                missing.append(f'{snapshot}/{check}: missing evidence')
            else:
                string(result['evidence'], f'{snapshot}/{check}.evidence')
            if result.get('passed') is False:
                check_failures[role].append(f'{snapshot}: check failed: {check}')
    return check_failures


def load(folder, roles, roster, required_checks):
    versions = obj(obj(read_json(folder / 'round.json'), 'round.json').get('versions'), 'versions')
    if set(versions) != roles:
        raise ValueError(f'{folder.name}: required version roles are {sorted(roles)}')
    for role, snapshot in versions.items():
        string(snapshot, f'versions.{role}')
    if 'candidate' in roles and versions['candidate'] == versions['current']:
        raise ValueError('candidate and current must have different snapshot IDs')
    labels = obj(read_json(folder / 'labels.json'), 'labels.json')
    for label, role in labels.items():
        string(role, f'labels.{label}')
    if not set(labels) <= {'X', 'Y'} or set(labels.values()) != roles or len(labels) != len(roles):
        raise ValueError(f'{folder.name}: labels must map X/Y to every required role exactly once')
    missing, reviewers = [], {}
    for path in sorted(folder.glob('*.json')):
        if path.name in {'labels.json', 'round.json', 'checks.json'}:
            continue
        name, answer = parse_answer(path, labels, roles, missing)
        if name not in roster or name in reviewers:
            raise ValueError(f'{path}: unknown or duplicate reviewer {name}')
        reviewers[name] = answer
    missing.extend(f'{name}: not run' for name in roster if name not in reviewers)
    check_failures = parse_checks(folder, versions, required_checks, missing)
    return {
        'folder': folder.name,
        'versions': versions,
        'reviewers': reviewers,
        'missing': missing,
        'check_failures': check_failures,
    }


def blockers(row, role, active):
    result = list(row['check_failures'][role])
    for name in active:
        reviewer = row['reviewers'].get(name)
        if reviewer is None:
            continue
        if reviewer['ready'].get(role) is not True:
            result.append(f'{name}: {role} not ready to ship')
        for finding in reviewer['findings'].get(role, []):
            if finding.get('severity') == 'major':
                result.append(
                    f'{name}: {finding.get("where", "?")}: {finding.get("problem", "?")} → {finding.get("fix", "?")}'
                )
    return result


def finish(status, code, messages=()):
    print(f'RESULT: {status}')
    for message in dict.fromkeys(messages):
        print(f'- {message}')
    return code


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


def latest_final_folder(run):
    """Earlier final checks stay on disk as history: final-check, final-check-2, final-check-3..."""
    folders = [p for p in run.iterdir() if p.is_dir() and re.fullmatch(r'final-check(-\d+)?', p.name)]
    return max(folders, key=lambda p: int(p.name.split('-')[2]) if p.name.count('-') == 2 else 1, default=None)


def decide_rounds(folders, roster, checks, panel_missing, advisory):
    """Load the rounds in order and decide which snapshot each one retains.

    A --advisory reviewer only affects the latest round: earlier decisions stand.
    """
    rows, seen, retained, baseline_missing = [], set(), [], []
    for index, folder in enumerate(folders):
        roles = {'current'} if index == 0 else {'current', 'candidate'}
        row = load(folder, roles, roster, checks)
        versions = row['versions']
        row['missing'].extend(panel_missing)
        if index == 0:
            retained.append(versions['current'])
            seen.add(versions['current'])
            baseline_missing = list(row['missing'])
        else:
            row['missing'].extend(baseline_missing)
            if versions['current'] != retained[-1]:
                raise ValueError(f'{folder.name}: current must be best retained snapshot {retained[-1]}')
            if versions['candidate'] in seen:
                raise ValueError(f'{folder.name}: candidate snapshot ID was already reviewed')
            seen.add(versions['candidate'])
        latest = index == len(folders) - 1
        if latest and advisory:
            row['missing'].append('required reviewers marked advisory: ' + ', '.join(advisory))
        voters = [name for name in roster if not (latest and name in advisory)]
        row['votes'] = sum(
            row['reviewers'][name]['preferred'] == 'candidate' for name in voters if name in row['reviewers']
        )
        promote = (
            index > 0
            and not row['missing']
            and not row['check_failures']['candidate']
            and row['votes'] * 2 > len(roster)
        )
        if promote:
            retained.append(versions['candidate'])
        row['kept'] = 'candidate' if promote else 'current'
        row['best'] = retained[-1]
        row['decision'] = (
            'INCOMPLETE' if row['missing'] else ('BASELINE' if index == 0 else 'KEEP' if promote else 'REVERT')
        )
        rows.append(row)
    return rows, retained


def load_final_check(run, roster, checks, retained):
    """Return the final check of the retained version, or None if there is none yet."""
    folder = latest_final_folder(run)
    if folder is None:
        return None
    final = load(folder, {'original', 'final'}, roster, checks)
    if final['versions']['original'] != retained[0] or final['versions']['final'] not in retained:
        raise ValueError(f'{folder.name} must compare the original with a retained snapshot')
    if final['versions']['final'] != retained[-1]:
        print(f'{folder.name} checked an earlier snapshot; a newer version was kept since then.\n')
        return None
    return final


def print_rounds(rows, panel_size):
    print('## Rounds\n')
    print('| Round | Current snapshot | Candidate snapshot | Candidate votes / full panel | Decision | Best snapshot |')
    print('|---|---|---|---|---|---|')
    for row in rows:
        versions = row['versions']
        print(
            f'| {row["folder"]} | {versions["current"]} | {versions.get("candidate", "—")} | '
            f'{row["votes"]} / {panel_size} | {row["decision"]} | {row["best"]} |'
        )


def print_findings(row):
    print('\n## Findings on the retained version\n')
    for name, reviewer in row['reviewers'].items():
        findings = reviewer['findings'].get(row['kept'])
        if findings is None:
            counts = 'not provided'
        else:
            counts = ', '.join(
                f'{severity}: {sum(f.get("severity") == severity for f in findings)}'
                for severity in ('major', 'minor', 'nit')
            )
        print(f'- {name}: {counts}; ready: {reviewer["ready"].get(row["kept"])}')


def tally(args):
    run = Path(args.run)
    roster, checks = config(run)
    if set(args.advisory) - set(roster):
        raise ValueError('unknown advisory reviewer')
    panel_missing = []
    if len(roster) < 3 or len(set(roster.values())) < 3:
        panel_missing.append('full council requires at least three reviewers from three distinct providers')
    folders = round_folders(run)
    # --advisory applies to the latest assessment: a still-valid final check, otherwise the last round.
    rows, retained = decide_rounds(folders, roster, checks, panel_missing, ())
    final = load_final_check(run, roster, checks, retained)
    round_advisory = () if final is not None else tuple(args.advisory)
    if round_advisory:
        rows, retained = decide_rounds(folders, roster, checks, panel_missing, round_advisory)
    print_rounds(rows, len(roster))
    original, best = retained[0], retained[-1]
    last = rows[-1]
    pending = list(last['missing'])
    issues = blockers(last, last['kept'], [name for name in roster if name not in round_advisory])
    print(f'\nBEST: {best}')
    print_findings(last)
    plateau = len(rows) >= 3 and all(row['decision'] == 'REVERT' for row in rows[-2:])
    review = 'INCOMPLETE' if pending else 'READY' if not issues else 'PLATEAU' if plateau else 'CONTINUE'
    print(f'REVIEW: {review}')
    final_issues, final_wins = [], False
    if final is not None:
        active = [name for name in roster if name not in args.advisory]
        final_missing = final['missing'] + panel_missing
        if args.advisory:
            final_missing.append('required reviewers marked advisory: ' + ', '.join(args.advisory))
        final_issues = blockers(final, 'final', active)
        votes = sum(r['preferred'] == 'final' for name, r in final['reviewers'].items() if name in active)
        unchanged = original == best
        final_wins = unchanged or votes * 2 > len(roster)
        status = 'INCOMPLETE' if final_missing else 'COMPLETE'
        print(f'FINAL CHECK: {status}; final preferred by {votes} / {len(roster)}')
        if unchanged:
            print(
                'Final snapshot equals original: no improvement is claimed; readiness still requires full verification.'
            )
        pending.extend(final_missing)
    elif review in ('READY', 'PLATEAU') or args.finalize:
        pending.append('final-check required before finishing; review readiness alone is not DONE')
    if pending:
        return finish('INCOMPLETE', 4, pending + issues + final_issues)
    if final is not None and not final_wins:
        reason = 'final version did not win over the original; show both to the user'
        return finish('REVIEW_REQUIRED', 5, [reason] + issues + final_issues)
    if final is not None and not issues and not final_issues:
        return finish('DONE', 0)
    if plateau:
        return finish('PLATEAU', 3, issues + final_issues)
    return finish('CONTINUE', 1, issues + final_issues)


def main(argv=None):
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', help='the run folder')
    parser.add_argument(
        '--advisory',
        action='append',
        default=[],
        help='reviewer whose latest answer cites things that are not there; keeps the result INCOMPLETE (repeatable)',
    )
    parser.add_argument('--finalize', action='store_true', help='require the final check when stopping on budget')
    args = parser.parse_args(argv)
    try:
        return tally(args)
    except Incomplete as error:
        return finish('INCOMPLETE', 4, [str(error)])
    except (ValueError, OSError) as error:
        return finish('INVALID', 2, [str(error)])


if __name__ == '__main__':
    sys.exit(main())
