#!/usr/bin/env python3
"""Tally the reviewers' answers of a blind-refine run and decide what happens next.

No scores anywhere: reviewers only say which version they would ship, whether it is
ready, and what is wrong with each version, by severity.

Expected run folder layout:

    <run>/round-0/labels.json        {"X": "current"}
    <run>/round-0/<reviewer>.json    the JSON block from the brief
    <run>/round-1/labels.json        {"X": "candidate", "Y": "current"}   (shuffled every round)
    <run>/round-1/...
    <run>/final-check/labels.json    optional: {"X": "final", "Y": "original"}

Usage:
    python tally.py <run> [--advisory "Gemini Argon"]

Exit code: 0 = DONE (the kept version is ready), 1 = CONTINUE, 2 = bad input data,
3 = PLATEAU (the candidate lost two rounds in a row).
"""
import argparse
import json
import re
import sys
from pathlib import Path

SEVERITIES = ("major", "minor", "nit")
ROLES = {"current", "candidate", "original", "final"}


def load(folder: Path):
    """Read labels.json and the reviewers' JSON files of one folder."""
    labels_path = folder / "labels.json"
    if not labels_path.exists():
        raise ValueError(f"missing {labels_path}")
    labels = json.loads(labels_path.read_text(encoding="utf-8"))
    bad = sorted(set(labels.values()) - ROLES)
    if bad:
        raise ValueError(f"{labels_path}: unknown version names {', '.join(bad)} (use {', '.join(sorted(ROLES))})")
    reviewers = {}
    for f in sorted(folder.glob("*.json")):
        if f.name == "labels.json":
            continue
        data = json.loads(f.read_text(encoding="utf-8"))
        name = data.get("reviewer") or f.stem
        if name in reviewers:
            raise ValueError(f"{f}: reviewer '{name}' already has a file in {folder.name}")
        # labels X/Y are reshuffled every round: map them to real versions right away
        preferred = data.get("preferred")
        if preferred is not None and preferred not in labels:
            raise ValueError(f"{f}: preferred label {preferred} not in labels.json")
        ready, findings = {}, {}
        for label, value in (data.get("ready_to_ship") or {}).items():
            if label not in labels:
                raise ValueError(f"{f}: label {label} not in labels.json")
            ready[labels[label]] = bool(value)
        for label, items in (data.get("findings") or {}).items():
            if label not in labels:
                raise ValueError(f"{f}: label {label} not in labels.json")
            for item in items:
                if item.get("severity") not in SEVERITIES:
                    raise ValueError(f"{f}: severity must be one of {', '.join(SEVERITIES)}")
            findings[labels[label]] = items
        if preferred is None and len(labels) == 1:
            preferred = next(iter(labels))
        reviewers[name] = {
            "preferred": labels.get(preferred) if preferred else None,
            "ready": ready,
            "findings": findings,
        }
    if not reviewers:
        raise ValueError(f"no reviewer files in {folder}")
    return set(labels.values()), reviewers


def round_number(p: Path):
    m = re.fullmatch(r"round-(\d+)", p.name)
    return int(m.group(1)) if m else None


def decide(versions, reviewers, gating):
    """Which version survives this round, and how many gating reviewers backed it."""
    votes = [r["preferred"] for n, r in reviewers.items() if n in gating]
    if "candidate" not in versions:
        return "current", None
    wins = votes.count("candidate")
    return ("candidate" if wins * 2 > len(votes) else "current"), (wins, len(votes))


def count(findings, severity):
    return sum(1 for f in findings if f.get("severity") == severity)


def main():
    # the Windows console defaults to cp1252 and cannot print every character
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--advisory", action="append", default=[], help="advisory-only reviewer (repeatable)")
    a = ap.parse_args()

    run = Path(a.run)
    if not run.is_dir():
        print(f"No such folder: {run}", file=sys.stderr)
        return 2
    folders = sorted((p for p in run.iterdir() if p.is_dir() and round_number(p) is not None), key=round_number)
    if not folders:
        print(f"No round-N folders in {run}", file=sys.stderr)
        return 2
    try:
        rounds = [(round_number(f), *load(f)) for f in folders]
        final_check = load(run / "final-check") if (run / "final-check").is_dir() else None
    except (ValueError, json.JSONDecodeError) as e:
        print(f"Bad input data: {e}", file=sys.stderr)
        return 2

    # 1. history: which version survived each round
    print("## Rounds\n")
    print("| Round | Candidate preferred by | Kept |")
    print("|---|---|---|")
    outcomes = []
    for n, versions, reviewers in rounds:
        gating = [r for r in reviewers if r not in a.advisory]
        kept, tally = decide(versions, reviewers, gating)
        outcomes.append((kept, tally))
        print(f"| {n} | {'n/a' if tally is None else f'{tally[0]} of {tally[1]}'} | {kept} |")

    # 2. the last round, reviewer by reviewer, about the version that survives
    n, versions, reviewers = rounds[-1]
    gating = [r for r in reviewers if r not in a.advisory]
    kept, tally = outcomes[-1]
    print(f"\n## Round {n}: findings on the kept version ({kept})\n")
    print("| Reviewer | Prefers | Major | Minor | Nit | Ready to ship |")
    print("|---|---|---|---|---|---|")
    blockers = []
    for name, r in reviewers.items():
        f = r["findings"].get(kept, [])
        ready = r["ready"].get(kept)
        label = f"{name} (advisory)" if name in a.advisory else name
        print(f"| {label} | {r['preferred'] or 'n/a'} | {count(f, 'major')} | {count(f, 'minor')} | "
              f"{count(f, 'nit')} | {'yes' if ready else 'no' if ready is False else 'n/a'} |")
        if name in gating:
            if count(f, "major"):
                blockers.append(f"{name}: {count(f, 'major')} major finding(s)")
            if not ready:
                blockers.append(f"{name}: not ready to ship")

    majors = [(name, x) for name, r in reviewers.items() if name in gating
              for x in r["findings"].get(kept, []) if x.get("severity") == "major"]
    if majors:
        print("\n## Major findings on the kept version\n")
        for name, x in majors:
            print(f"- **{name}**, {x.get('where', '?')}: {x.get('problem', '')} → {x.get('fix', '')}")

    # 3. final check: the finished version against the original, both blind
    if final_check:
        versions, fc = final_check
        votes = [r["preferred"] for name, r in fc.items() if name not in a.advisory]
        wins = votes.count("final")
        print(f"\n## Final check\n\nThe final version is preferred over the original by {wins} of {len(votes)} reviewers.")
        if wins * 2 <= len(votes):
            print("WARNING: the reviewers do not prefer the final version; look at what drifted before you ship it.")

    print()
    if tally is not None:
        print(f"DECISION: {'KEEP the candidate' if kept == 'candidate' else 'REVERT to the current version'}"
              f" ({tally[0]} of {tally[1]} reviewers prefer the candidate)")
    if len(gating) < 2:
        print("WARNING: fewer than two gating reviewers; the decision carries little weight.")
    last_two = [k for k, t in outcomes[-2:] if t is not None]
    if len(last_two) == 2 and all(k == "current" for k in last_two):
        print("\nRESULT: PLATEAU (the candidate lost two rounds in a row)")
        return 3
    if not blockers:
        print("\nRESULT: DONE (no major findings, every gating reviewer would ship it)")
        return 0
    print("\nRESULT: CONTINUE")
    for b in blockers:
        print(f"- {b}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
