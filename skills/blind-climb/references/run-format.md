# Run data contract

The files `scripts/tally.py` reads. They are private to the parent agent: reviewers get only the staged versions and the review brief, never these files. The decision rules are in Steps 4 and 6 of `SKILL.md`; this file only defines the data.

## `run.json`

Write it before dispatching anyone, with the model names actually resolved for this run:

```json
{
  "reviewers": [
    {"name": "Reviewer One", "provider": "anthropic"},
    {"name": "Reviewer Two", "provider": "openai"},
    {"name": "Reviewer Three", "provider": "google"}
  ],
  "checks": ["build", "accessibility"]
}
```

Every declared reviewer is required, even if it never answers. Fewer than three distinct providers is INCOMPLETE. `checks: []` means no programmatic check applies; never drop a failing check or a reviewer to get a result.

## Each round

Folders are `round-0`, `round-1`, … with no gaps.

`round.json` names immutable snapshots (a path or a scoped commit). Round 0 has only `current`, the original. Every later round has `current`, which must be the BEST snapshot even after a rejected attempt, and a `candidate` ID never used before.

```json
{"versions": {"current": "snapshots/v0", "candidate": "snapshots/v2"}}
```

`labels.json` maps `X` and `Y` one-to-one to the roles, shuffled every round. Round 0 has a single label mapped to `current`. References (R1, R2) are context in the brief and never appear here.

```json
{"X": "candidate", "Y": "current"}
```

`checks.json` holds actual results for every snapshot in the round. Each declared check needs a literal boolean and non-empty evidence (command output, a measurement or a log path). The file may be left out only when `checks` is empty.

```json
{
  "snapshots": {
    "snapshots/v0": {
      "build": {"passed": true, "evidence": "original-build.log: exit 0"},
      "accessibility": {"passed": false, "evidence": "original-axe.json: serious contrast issue"}
    },
    "snapshots/v2": {
      "build": {"passed": true, "evidence": "candidate-build.log: exit 0"},
      "accessibility": {"passed": true, "evidence": "candidate-axe.json: no serious findings"}
    }
  }
}
```

`<reviewer>.json` is the reviewer's JSON block from [review-brief.md](review-brief.md), saved untouched. The file name can be a short alias, but `reviewer` must match a name in `run.json` exactly, once per round. Every listed version needs a `ready_to_ship` boolean and a `findings` list (`[]` means nothing found; a missing list is not an empty one). Each finding has `severity` (`major`, `minor` or `nit`), `where`, `problem` and `fix`.

```json
{
  "reviewer": "Reviewer One",
  "preferred": "X",
  "why": "Specific observed reasons for choosing X.",
  "ready_to_ship": {"X": true, "Y": false},
  "findings": {
    "X": [],
    "Y": [{"severity": "major", "where": "contact form", "problem": "Submit fails", "fix": "Restore submission"}]
  }
}
```

`preferred` is `X`, `Y` or `tie`; in round 0 it is the single label or `null`.

The script checks the chain of snapshot IDs, not the snapshots' contents: keep the real snapshots and stage exactly those. A round's files don't change once all its answers are in.

## Final check

Same files in `final-check/`, with the roles `original` and `final`:

```json
{"versions": {"original": "snapshots/v0", "final": "snapshots/v2"}}
```

`original` must be the round-0 snapshot and `final` a retained one. If a newer version is kept afterwards, leave the folder as it is and run the next check in `final-check-2/`, then `final-check-3/`; the highest number counts. If nothing was ever kept, both roles may point at the original.

## Validation

- **INCOMPLETE**: a required file, reviewer, readiness value, findings list, finding field, check result or final check is missing, a reviewer is marked `--advisory`, or the panel has fewer than three providers.
- **INVALID**: malformed or duplicate JSON keys, an unknown reviewer, label, role, severity or check, `"false"` or `0` instead of `false`, empty required strings, checks for a snapshot not in the round, or a broken snapshot chain.

Runs from older versions of this format report INCOMPLETE. Start a new run instead of editing their files.

## Command and exit codes

```bash
python scripts/tally.py <run-folder> [--advisory NAME] [--finalize]
```

| Exit | Result | What to do |
|---|---|---|
| 0 | DONE | Deliver the BEST snapshot. |
| 1 | CONTINUE | Fix the findings on the kept version (Step 5). |
| 2 | INVALID | Repair the data from the original answers and evidence; never make up results. |
| 3 | PLATEAU | Report what keeps failing. |
| 4 | INCOMPLETE | Collect what is missing; report only provisional findings. |
| 5 | REVIEW_REQUIRED | The final version didn't win the final check: show both to the user. |

When several apply, the first in this order wins: INCOMPLETE, REVIEW_REQUIRED, DONE, PLATEAU, CONTINUE. `REVIEW: READY` and `FINAL CHECK: COMPLETE` are printed separately; neither means DONE.
