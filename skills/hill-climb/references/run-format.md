# Run data contract

The files `scripts/aggregate.py` reads. They are private to the parent agent and never go in the judge staging folder. The selection and verdict rules are in Step 4 of `SKILL.md`; this file only defines the data.

## `run.json` and `rubric.json`

Write both before any judging, with the model names actually resolved for this run:

```json
{
  "mode": "climb",
  "judges": [
    {"name": "Judge One", "provider": "anthropic"},
    {"name": "Judge Two", "provider": "openai"},
    {"name": "Judge Three", "provider": "google"}
  ],
  "references": ["Category leader"],
  "checks": ["build", "accessibility"]
}
```

```json
["Hierarchy", "Typography", "Color", "Layout"]
```

- `mode` is `score` (exactly one round) or `climb`.
- Every declared judge is required, even if it never answers. Fewer than three distinct providers is INCOMPLETE.
- `references: []` only when no suitable reference exists; the scorecard then says the scores are absolute. `checks: []` means no programmatic check applies. Never empty either list to get a PASS.
- `ours` and `incumbent` are reserved and can't be reference names. Rubric categories are unique.

## Each round

Folders are `round-0`, `round-1`, … with no gaps.

`round.json` names immutable snapshots (a path or a scoped commit). Round 0 has `"incumbent": null`; every later round points at the BEST snapshot, even after a rejected attempt. Candidate IDs are never reused, the artifact behind an ID never changes after judging, and a round's files don't change once all its answers are in. The script checks the chain of IDs, not the snapshots' contents.

```json
{"candidate": "snapshots/v2", "incumbent": "snapshots/v0"}
```

`labels.json` maps uppercase labels one-to-one to items, shuffled every round. It always holds `ours` and every declared reference, plus `incumbent` after round 0.

```json
{"A": "incumbent", "B": "Category leader", "C": "ours"}
```

`checks.json` holds the candidate's actual results. Each declared check needs a literal boolean and non-empty evidence (command output, a measurement or a log path). The file may be left out only when `checks` is empty. Run the checks before paying for the jury: after round 0, a candidate that fails one isn't worth judging.

```json
{
  "candidate": "snapshots/v2",
  "results": {
    "build": {"passed": true, "evidence": "npm run build: exit 0; build.log"},
    "accessibility": {"passed": false, "evidence": "axe: serious contrast finding; axe.json"}
  }
}
```

`<judge>.json` is the judge's JSON block from [judge-brief.md](judge-brief.md), saved untouched. The file name can be a short alias, but `judge` must match a name in `run.json` exactly, once per round. Every item needs a score in every category, as a JSON number from 1 to 10. After round 0, `ranking.order` lists every label once, best first; labels in the same group are tied.

## Validation

- **INCOMPLETE**: a required file, judge, score, ranking or check result is missing, a judge is marked `--advisory`, or the panel has fewer than three providers.
- **INVALID**: malformed or duplicate JSON keys, numeric strings, NaN or infinity, an unknown judge, label, category or check, a repeated label in a ranking, or a broken snapshot chain.

Runs from older versions of this format report INCOMPLETE or INVALID. Start a new run instead of editing their files.

## Command and exit codes

```bash
python scripts/aggregate.py <run-folder> --target 9 [--advisory NAME] [--tolerance 0] [--noise 0.5] [--plateau 0.3]
```

| Exit | Result | What to do |
|---|---|---|
| 0 | PASS | Deliver the BEST snapshot. |
| 1 | FAIL | Read KEEP/REJECT and BEST separately, then fix (Step 5) or stop. |
| 2 | INVALID | Repair the data from the original answers and evidence; never make up results. |
| 3 | INCOMPLETE | Collect what is missing; report only provisional findings. |
