# Run data contract

Read before setting up a blind-climb run or calling `scripts/tally.py`. These files are private to the parent. Reviewers receive only staged artifacts and the review brief, never the manifest, role mappings, snapshot IDs or past decisions.

## Panel and required checks

Create `run.json` before dispatching reviewers. Replace these example names with the actual resolved model names:

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

Every declared reviewer is required, even if no answer arrives. At least three distinct providers are required for promotion or DONE. A degraded panel can report provisional findings but stays INCOMPLETE. `--advisory NAME` marks a reviewer's answer in the latest assessment (the last round, or a final check still valid for the retained version) as unreliable, without reducing the panel or the majority needed. Earlier decisions stand. A typo in this option is INVALID.

`checks: []` explicitly declares that no programmatic check applies. Never delete a required check or reviewer to obtain success. Duplicate identities or check names are INVALID.

## Snapshots and labels

Use consecutive folders `round-0`, `round-1`, etc. Every round has `round.json`:

```json
{"versions": {"current": "snapshots/v0", "candidate": "snapshots/v2"}}
```

Round 0 has only `current`, the immutable original snapshot. Each later round has exactly `current` and `candidate`. `current` must identify the last retained snapshot, including after rejected or incomplete attempts. A candidate ID must be new and distinct from current; never overwrite or reuse a reviewed snapshot. Complete the baseline assessment before promoting a candidate. Baseline checks may fail: the original remains the seed to repair, not an approved deliverable.

`labels.json` maps anonymous labels one-to-one to roles, shuffled each round:

```json
{"X": "candidate", "Y": "current"}
```

The baseline has one label (`X` or `Y`) mapped to `current`. References R1/R2 are context in the brief, not eligible choices and not included in this mapping.

The script verifies snapshot identity chains, not actual file contents. The parent must preserve the real snapshots and ensure staged files match the recorded IDs. Finalized round records are immutable; finish collecting a provisional round's required answers before finalizing it. New attempts receive new round folders and candidate IDs.

## Programmatic results

Every round and final check has `checks.json`, with actual results for each listed snapshot:

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

Required checks must have literal boolean results and non-empty evidence (command output, measurement or log path). Missing results/evidence are INCOMPLETE; malformed values are INVALID. Evidence for an unreviewed snapshot is INVALID. The file may be omitted only when the manifest explicitly declares no checks.

Run checks before paying for a review. Fix or discard a failing candidate before dispatching. An improvement can replace an original with failed checks if the candidate's own checks pass; a discarded failing candidate does not prevent finishing with a ready incumbent. Promotion is blocked by incomplete records. Readiness and DONE require passing checks for the retained/final snapshot; the original may still fail in the final comparison.

## Reviewer answers

Save raw answers as `<reviewer>.json`; filenames may be short aliases. `reviewer` must exactly match one declared name, once per folder. Follow `review-brief.md`:

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

Use `X`, `Y` or `tie` for a paired preference; baseline preference may be its single label or null/omitted. `why`, readiness and findings are still required for the baseline. Every listed version requires a literal readiness boolean and an explicit findings list. Missing findings do not mean an empty list. Findings require `severity` (`major`, `minor`, `nit`), `where`, `problem` and `fix`. Missing fields are INCOMPLETE; wrong types, empty required strings, unexpected labels/severities, duplicate reviewers and duplicate JSON keys are INVALID. Strings such as `"false"`, integers and null are not readiness booleans. No ratings are requested or calculated.

## Final check

After `REVIEW: READY`, a plateau or the budget limit, dispatch fresh reviewers on original versus the best retained snapshot. `final-check/round.json`:

```json
{"versions": {"original": "snapshots/v0", "final": "snapshots/v2"}}
```

Include shuffled `labels.json` (`{"X":"final","Y":"original"}` or reverse), the full panel's raw answers and checks for both snapshots. A final check naming a snapshot that was never retained, or a different original, is INVALID. If a newer version is kept after a final check, that check no longer counts: leave its folder untouched and run a new one in `final-check-2/`, then `final-check-3/`. The highest number is the one that counts. If no version was changed, both roles may point to the original snapshot: still collect the full readiness assessment and checks, but make no claim of improvement and do not require a preference between identical copies.

`REVIEW: READY` is separate from DONE. DONE requires a complete panel, passing retained/final checks, every reviewer ready to ship the retained/final version, no major findings in either assessment, and a strict majority preferring final over original (except the unchanged-original case). A tied/lost final comparison reports REVIEW_REQUIRED for the user's decision, never DONE. A completed final check with unresolved major findings remains CONTINUE or PLATEAU.

## Command and exit codes

```bash
python scripts/tally.py <run-folder> [--advisory NAME] [--finalize]
```

`--finalize` requires the final check when stopping on budget before readiness or plateau. READY and PLATEAU already require the final check automatically. Ordinary CONTINUE rounds do not require it yet. `FINAL CHECK: COMPLETE` means all required evidence was supplied, not that it passed. `BEST` identifies the retained snapshot, including when the last candidate lost.

| Exit | Result | Meaning |
|---|---|---|
| 0 | DONE | Readiness and final verification both passed. |
| 1 | CONTINUE | Complete review still has unresolved readiness/check issues. |
| 2 | INVALID | Malformed data or inconsistent snapshot identity chain. |
| 3 | PLATEAU | Two consecutive complete candidate rejections with unresolved issues; final check supplied. |
| 4 | INCOMPLETE | Missing required data, panel or final check. Incomplete rounds cannot promote; incomplete final verification prevents DONE. |
| 5 | REVIEW_REQUIRED | Final comparison did not prefer the final version. Show both to the user. |

INCOMPLETE takes precedence over success, plateau or human escalation. A clean retained version takes precedence over plateau: verify it rather than continuing for its own sake. A budget stop with a completed final check can still be CONTINUE; report the remaining issues and the stop reason honestly.

Read KEEP/BEST separately from the overall result: a complete round may legitimately retain a candidate while the run remains INCOMPLETE because its final check is still missing. That missing final check does not undo a valid local selection.

Runs from older versions of this format report INCOMPLETE. Start a new run instead of editing their files.
