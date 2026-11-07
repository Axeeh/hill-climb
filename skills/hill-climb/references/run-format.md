# Run data contract

Read before creating a run or calling `scripts/aggregate.py`. All files here are private to the parent, never included in the judge staging folder. The manifest declares what must exist, whatever answers arrive.

## Required run files

`run.json` (use the actual council model names resolved for this run):

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

Mode is `score` or `climb`. All declared judges are required, even if they never produce a file. A panel with fewer than three distinct providers is INCOMPLETE. `references: []` is allowed only when no suitable reference exists; disclose absolute-only scoring in the report. `checks: []` explicitly means no programmatic check applies. Don't empty these lists to get a PASS.

`rubric.json` contains the exact, unique category names:

```json
["Hierarchy", "Typography", "Color", "Layout"]
```

## Required round files

Use consecutive folders starting at `round-0`. Score mode has just `round-0`.

`round-N/round.json` identifies immutable snapshots (paths or scoped commit IDs may be used). The baseline has `"incumbent": null`. Every subsequent round must point to the snapshot last selected KEEP, even if the previous attempt was rejected:

```json
{"candidate": "snapshots/v2", "incumbent": "snapshots/v0"}
```

Candidate IDs must be unique per round; never change the artifact behind an ID after judging. The aggregator verifies the ID chain, not the contents of snapshots. The parent must ensure staged files and check evidence belong to those snapshots.

`round-N/labels.json` is a one-to-one private mapping. Shuffle labels each time:

```json
{"A": "incumbent", "B": "Category leader", "C": "ours"}
```

In round 0 and Score mode, omit `incumbent`. Include every declared external reference in every round. `ours` is the candidate; `incumbent` is the previous best, never an external benchmark. Labels use uppercase letters only.

`round-N/checks.json` records actual results tied to the candidate, with a command result, measurement or log path as evidence:

```json
{
  "candidate": "snapshots/v2",
  "results": {
    "build": {"passed": true, "evidence": "npm run build: exit 0; build.log"},
    "accessibility": {"passed": false, "evidence": "axe: serious contrast finding; axe.json"}
  }
}
```

Every declared check requires a literal boolean and non-empty evidence. Missing results are INCOMPLETE; false results block retention and PASS. This file may be omitted if the manifest explicitly declares no checks. Record checks before asking the jury. Round 0 is judged even if it fails a check, because it is the starting point; after that, don't pay for a review of a candidate already known to fail.

`round-N/<judge>.json` is the raw JSON from the brief. The `judge` name must match one roster entry exactly; filenames may be short aliases. Each reviewer must score every listed item in every rubric category. Scores must be JSON numbers in [1, 10]; strings, booleans, NaN and infinity are invalid. Duplicate JSON keys, duplicate judge identities and unexpected categories/items are invalid.

Every answer also ranks all the items, best first. Items in one group are equal:

```json
"ranking": {"order": [["B"], ["C", "A"]], "reason": "Specific evidence for the order."}
```

After the baseline the script compares `ours` and `incumbent` in that ranking: the same group is a tie, and references can rank anywhere without affecting selection. A missing ranking or item is INCOMPLETE; an unknown or repeated label is INVALID. Do not give the reviewer this mapping or earlier scores.

## Selection and verdict

- Baseline: round 0 is the first retained snapshot even if it misses the target or fails a check, because it is what you start from. It cannot PASS with a failed check, and its full jury answers and check results are required before any candidate can be promoted.
- Later candidates: all required inputs must be present and checks must pass; a strict majority of the entire declared panel must prefer the candidate. Otherwise retain the incumbent. Ties never promote a candidate.
- Incomplete screening rounds cannot promote a candidate. Complete the baseline before producing candidates; later partial screenings may be logged as rejected attempts, with the next candidate still based on BEST. Finish collecting the same round's required answers before treating it as finalized; do not edit finalized round files.
- PASS requires a retained candidate plus every required judge reaching the absolute target and matching its own best external reference in each category. The incumbent comparison serves selection; it is not included in the external-reference maximum.
- `--advisory NAME` marks a judge's answer in the latest round as unreliable. Earlier rounds keep their decisions, and the latest round stays INCOMPLETE until that judge has a valid review for it.

Command: `python scripts/aggregate.py <run-folder> --target 9`. Options: `--tolerance 0`, `--noise 0.5`, `--plateau 0.3`. All numeric options must be finite and in the allowed range. Historical score regression/plateau warnings remain diagnostic; blind preference selects the version.

| Exit | Result | Action |
|---|---|---|
| 0 | PASS | Target achieved by a retained version with the complete panel and checks. |
| 1 | FAIL | Complete evaluation, but target/reference/check/selection condition failed. Read KEEP/REJECT and BEST separately. |
| 2 | INVALID | Repair malformed data or wrong snapshot lineage from original evidence; never fabricate results. |
| 3 | INCOMPLETE | Collect missing evidence; report provisional findings only. |

Runs from older versions of this format report INCOMPLETE or INVALID. Start a new run instead of editing their files.
