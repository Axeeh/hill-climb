#!/usr/bin/env python3
"""Aggregate the judges' scores of a hill climb and decide PASS / FAIL.

Expected run folder layout:

    <run>/round-0/labels.json      {"A": "ours", "B": "Claude Code", "C": "Codex"}
    <run>/round-0/<judge>.json     the JSON block from the brief (keys: judge, items)
    <run>/round-1/...

Usage:
    python aggregate.py <run> [--target 9] [--ours ours] [--advisory "Gemini Argon"]
                              [--tolerance 0] [--plateau 0.3]

Prints markdown tables ready for scorecard.md and the result, which is also the exit code:
0 = PASS, 1 = FAIL, 2 = bad input data.
"""
import argparse
import json
import re
import sys
from pathlib import Path


def load_round(folder: Path):
    """Read labels.json and the judges' JSON files of one round."""
    labels_path = folder / "labels.json"
    if not labels_path.exists():
        raise ValueError(f"missing {labels_path}")
    labels = json.loads(labels_path.read_text(encoding="utf-8"))
    judges = {}
    for f in sorted(folder.glob("*.json")):
        if f.name == "labels.json":
            continue
        data = json.loads(f.read_text(encoding="utf-8"))
        name = data.get("judge") or f.stem
        # labels A/B/C are reshuffled every round: map them to real names right away
        by_name = {}
        for label, item in data.get("items", {}).items():
            if label not in labels:
                raise ValueError(f"{f}: label {label} not in labels.json")
            by_name[labels[label]] = {k: float(v) for k, v in item.get("scores", {}).items()}
        judges[name] = by_name
    return judges


def round_number(p: Path):
    m = re.fullmatch(r"round-(\d+)", p.name)
    return int(m.group(1)) if m else None


def fmt(x):
    return "n/a" if x is None else f"{x:.1f}"


def main():
    # the Windows console defaults to cp1252 and cannot print "≥"
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--target", type=float, default=9.0)
    ap.add_argument("--ours", default="ours", help="name of our item in labels.json")
    ap.add_argument("--advisory", action="append", default=[], help="advisory-only judge (repeatable)")
    ap.add_argument("--tolerance", type=float, default=0.0, help="allowed negative gap to the best reference")
    ap.add_argument("--plateau", type=float, default=0.3, help="minimum rise of the minimum score between rounds")
    a = ap.parse_args()

    run = Path(a.run)
    folders = sorted((p for p in run.iterdir() if p.is_dir() and round_number(p) is not None), key=round_number)
    if not folders:
        print(f"No round-N folders in {run}", file=sys.stderr)
        return 2
    try:
        rounds = [(round_number(f), load_round(f)) for f in folders]
    except (ValueError, json.JSONDecodeError) as e:
        print(f"Bad input data: {e}", file=sys.stderr)
        return 2

    everyone = sorted({j for _, js in rounds for j in js})
    gating = [j for j in everyone if j not in a.advisory]

    # 1. round table: per judge, the lowest category score of our item
    print("## Minimum score per round (ours)\n")
    print("| Judge | " + " | ".join(f"Round {n}" for n, _ in rounds) + " |")
    print("|---|" + "---|" * len(rounds))
    round_minimums = []
    for j in everyone:
        cells = []
        for _, js in rounds:
            s = js.get(j, {}).get(a.ours)
            cells.append(fmt(min(s.values())) if s else "not run")
        label = f"{j} (advisory)" if j in a.advisory else j
        print(f"| {label} | " + " | ".join(cells) + " |")
    for _, js in rounds:
        vals = [min(js[j][a.ours].values()) for j in gating if j in js and js[j].get(a.ours)]
        round_minimums.append(min(vals) if vals else None)

    # 2. final round: category by category, against the same judge's best reference
    n_final, final = rounds[-1]
    print(f"\n## Categories, round {n_final}\n")
    print("| Category | Ours (lowest judge) | Best reference (lowest judge) | Smallest per-judge gap |")
    print("|---|---|---|---|")
    reasons = []
    missing = [j for j in gating if j not in final or not final[j].get(a.ours)]
    for j in missing:
        reasons.append(f"{j}: not run in the final round")
    present = [j for j in gating if j not in missing]
    categories = sorted({c for j in present for c in final[j][a.ours]})
    for c in categories:
        ours_vals, gaps, bests = [], [], []
        for j in present:
            ours = final[j][a.ours].get(c)
            if ours is None:
                reasons.append(f"{j}: no score for '{c}'")
                continue
            ours_vals.append(ours)
            if ours < a.target:
                reasons.append(f"{j}: {c} = {ours:.1f} < {a.target:.1f}")
            refs = [v.get(c) for k, v in final[j].items() if k != a.ours and v.get(c) is not None]
            if refs:
                bests.append(max(refs))
                gaps.append(ours - max(refs))
                if ours - max(refs) < -a.tolerance:
                    reasons.append(f"{j}: {c} below the best reference ({ours:.1f} vs {max(refs):.1f})")
        print(f"| {c} | {fmt(min(ours_vals) if ours_vals else None)} | "
              f"{fmt(min(bests) if bests else None)} | "
              f"{('%+.1f' % min(gaps)) if gaps else 'no reference'} |")

    print()
    print("The gap is computed within each judge (ours minus that judge's best reference),"
          " because judges start from different baselines.")

    # 3. warnings: plateau, no references, too few judges
    print()
    valid = [m for m in round_minimums if m is not None]
    if len(valid) >= 3 and all(valid[i] - valid[i - 1] < a.plateau for i in (-1, -2)):
        print(f"WARNING: plateau, the minimum has not risen by {a.plateau} for two rounds ({', '.join(fmt(m) for m in valid[-3:])}).")
    has_refs = any(k != a.ours for j in present for k in final[j])
    if not has_refs:
        print("WARNING: no references in the final round; scores are absolute and tend to inflate.")
    if len(present) < 2:
        print("WARNING: fewer than two gating judges; the verdict carries little weight.")

    if reasons or not present:
        print("\nRESULT: FAIL")
        for r in dict.fromkeys(reasons):
            print(f"- {r}")
        return 1
    print(f"\nRESULT: PASS (every gating judge ≥ {a.target:.1f} in every category"
          + (", and ≥ the best reference)" if has_refs else ")"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
