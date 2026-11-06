---
name: blind-climb
description: Improve any artifact round after round with a blind, multi-provider review panel (the council skill) that never sees a score, a target or a loop. Each round fresh reviewers get two unlabelled versions in random order, pick the one they would ship, and list what is wrong with each by severity; the better version survives and the agreed findings are fixed. Stops when no reviewer finds anything major and all would ship it, on a plateau or on budget, then checks the final version blindly against the original. Works for UIs and websites, emails, social posts, proposals, code, prompts and skills, business plans and other writing. Use when the user says "blind climb", "blind refine", "refine this", "improve it without scores", "keep improving until the reviewers have nothing left", "blind review loop", "make it better, no grades" or worries that numbers bias the reviewers. Not for a scorecard or a number to beat (use hill-climb), or for a one-off second opinion (use council).
license: Unlicense
compatibility: Needs the council skill (bundled in this repo), an agent that can run subagents on models from other providers (T3 Code delegate_task or an equivalent harness), and Python 3.9+ for scripts/tally.py.
metadata:
  author: Axeeh
  version: "1.2.0"
  source: https://github.com/Axeeh/hill-climb
---

# Blind climb

The score-free sibling of `hill-climb`. A reviewer who is asked for a number anchors on it, drifts with it and can guess what the asker wants to hear. Here nobody in the panel scores anything or knows a loop is running: each round fresh reviewers see two versions, X and Y, in random order, say which one they would ship and what is wrong with each. The version they prefer survives, its agreed problems get fixed, and the next round compares the fix against it.

**The idea in one line:** let blind reviewers choose between two versions and say what's wrong, keep the one they choose, fix it, repeat until they have nothing major left.

It uses Theo Browne's `council` skill ([tstack](https://github.com/t3dotgg/tstack)) as the panel, and the blind, fresh, read-only rules from his hill-climbing method ([Agents Sucked At UI (Until Today)](https://youtu.be/xq0eB8vxeqk)).

## Step 1: set it up (before any review)

Write these down in the run log (Step 7) and show the user a 5-line summary before you start:

1. **Artifact**: exactly what is reviewed and how reviewers will see it (screenshots at mobile and desktop width, the text, a diff, the PDF).
2. **Programmatic checks**: build, tests, accessibility, length, anything a program can verify. They are **gates**: a candidate that fails one is fixed or dropped before any reviewer sees it.
3. **Context for the reviewers**: the audience, what the artifact must achieve, the medium. The same words every round.
4. **References** (optional): 1–2 strong examples of the same kind, shown as context.
5. **Guardrails**: what must not change or get worse (brand, real content, prices, legal text, accessibility, the agreed scope).
6. **Budget**: maximum rounds (default 5) and a rough cost limit.

Work on a branch, a worktree or a numbered copy (`v2`, `v3`). Never on the only copy.

Before reviewing, create mandatory `run.json` with the expected reviewers, their providers and required programmatic checks. Read [references/run-format.md](references/run-format.md) for the schemas. Declare every required reviewer before collecting answers; never infer the panel from whoever replies. An explicit empty check list means no check applies, not permission to drop failing checks.

## Step 2: the panel is the `council` skill

**Every round of review is one run of the `council` skill.** Read its `SKILL.md` and follow it for which models (the members named in the user's `AGENTS.md` or equivalent, otherwise the latest flagship of three providers), how to start them, read-only delegates and reporting an unreachable member instead of substituting it.

Where the two differ, these rules win:

- **No fixing inside council.** Council fixes known issues before it audits; here all changes happen in Step 5, so each round reviews fixed versions.
- **One council run = one round**, with **new delegates** every round. Council's "continue until all delegates are satisfied" loop is replaced by Steps 4–6.
- **The delegates' request is the review brief** ([references/review-brief.md](references/review-brief.md)), identical for each member.
- **Keep the raw answers**: save each delegate's JSON block untouched as `round-N/<reviewer>.json`. Decisions come from the script in Step 4, never from council's summary.
- **No scores, anywhere.** Council asks for a score out of 10 on code reviews: don't, not even "for the PR table". If the work ends in a PR, its `## Council review` table lists each member's choice and major findings per round (`kept candidate, 0 major`), never a number.
- If council can't reach three providers, say the run is degraded in the summary. A missing required reviewer or fewer than three distinct providers makes the result `INCOMPLETE`, never DONE or a candidate promotion.

## Step 3: blind, fresh, read-only

These rules matter more than the wording of the brief:

- **No numbers and no loop.** Never mention a score, a target, a round, a previous version or an improvement. The brief only asks which version to ship and what is wrong.
- **Blind to order.** Label the two versions X and Y in a new random order every round. Never say which one is newer or which one the agent wrote.
- **Best retained version.** Give every version an immutable snapshot ID and record its role in `round-N/round.json`. `current` must always be the best retained snapshot, even after a rejected candidate. Never overwrite a reviewed snapshot or silently compare against the last attempt. Snapshot IDs and role mappings stay private to the parent.
- **Blind files.** Copy each version into a new staging folder **outside the project and the run folder** (the system temp folder), named only by label: `X-390.png`, `Y-1440.png`, `X.md`. Tell reviewers to open nothing else. The run folder holds `labels.json` and earlier findings, so a reviewer that reads it is no longer blind. For code that only exists in the project, give each version as a copied file or excerpt, not a path into the repo.
- **Fresh context**: a new delegate every round, never a follow-up in an old thread, and no earlier findings.
- **Read-only**: reviewers look and report; the parent agent makes every change.

## Step 4: tally and decide

Save each reviewer's raw JSON, `round.json`, `labels.json` (`{"X": "candidate", "Y": "current"}`, shuffled), and `checks.json` with actual results and evidence tied to the snapshot IDs. Each answer must include literal readiness booleans and an explicit findings list for each version (`[]` means no findings). Missing data is never interpreted as approval. Then run the bundled script from this skill's folder:

```bash
python scripts/tally.py <run-folder> [--advisory "<reviewer name>"] [--finalize]
```

It prints which version survived each round, the findings on the kept version per reviewer, and a result:

- **KEEP or REVERT**: the candidate survives only with complete data, its required checks passing, and **more than half of the entire declared panel** preferring it. A tie keeps the current version. `BEST` prints the retained snapshot ID; the script verifies the snapshot chain.
- **REVIEW: READY**: on the kept version, all required checks pass, no required reviewer reports a `major` finding and every required reviewer would ship it. Run Step 6's final check; READY alone is not DONE.
- **DONE** (exit 0): the retained version meets READY and the complete final check confirms it is ready, has no major findings, passes its checks and wins over the original. If the retained version is the unchanged original, the final check still verifies readiness but makes no improvement claim.
- **CONTINUE** (exit 1): fix and run another round.
- **PLATEAU** (exit 3): the candidate lost two rounds in a row. Stop and report what keeps failing instead of burning rounds.
- **INCOMPLETE** (exit 4): missing manifest, required reviewer, readiness value, findings list, check evidence or required final check. Partial findings may inform work, but cannot promote a candidate or finish the run.
- **INVALID** (exit 2): malformed JSON, duplicate keys/reviewers, unexpected labels or snapshot IDs, wrong types (including `"false"` instead of `false`) or malformed findings. Repair from original evidence; never invent results.
- **REVIEW_REQUIRED** (exit 5): the complete final check does not prefer the final version. Show the user both versions and the findings; do not claim completion.

The script prints review readiness separately from the overall result. At READY or a plateau, a missing final check yields INCOMPLETE. Use `--finalize` when stopping because of budget to require the same final check even if review issues remain. A completed final check does not erase unresolved issues or turn a budget stop into DONE.

A reviewer that cites things that aren't there (wrong lines, a passage that doesn't exist, a problem already fixed) becomes advisory: pass `--advisory` and say so in the summary. The required panel remains INCOMPLETE until that member has a valid gating review; excluding its answer cannot manufacture a majority or DONE.

## Step 5: fix

1. **Choose what to fix**, from the findings on the kept version: first the `major` findings two or more reviewers agree on, then any other `major`, then `minor` findings two or more reviewers share. A finding only one reviewer has waits unless it is clearly right. `nit`s are taste: skip them unless the user cares. Reject anything that breaks a guardrail or grows the scope, and note why.
2. Apply the fixes to a copy of the kept version: that is the next **candidate**. If you hand the fixing to a subagent, give it the findings and the context from Step 1, never a score or a target, for the same reason as the reviewers.
3. Run the programmatic checks. For anything visual, look at it yourself, at mobile width first.
4. Start the next round from Step 3: the kept version is `current`, the fix is `candidate`.

Round 0 has only the starting version: reviewers list its problems, the first fix becomes the first candidate. Record its checks even if they fail: the original is the seed, not a claim of readiness. Complete the baseline assessment before promoting a candidate. Only a candidate whose own checks pass can replace it. Partial rounds cannot promote; the next attempt must still use BEST.

## Step 6: finish

- **Final check.** After REVIEW: READY, a plateau or the budget, run one more fresh council run with the **original** and the **best retained snapshot** as X and Y, blind, in a `final-check/` folder (`{"X": "final", "Y": "original"}`, shuffled). Include its `round.json`, full panel answers and check evidence for the exact snapshots. A stale final check against an earlier candidate is INVALID. Small steps can each win and still drift somewhere worse. Without a majority preferring the final version, `tally.py` reports REVIEW_REQUIRED: show the user both and let them decide. For an unchanged original, full readiness verification is still required but preference is immaterial. Rerun the tally after collecting the final check.
- **Human checkpoints.** After a kept candidate, show the user before and after side by side with the changes annotated. The user's taste beats the panel: a correction like "too grey, bring the colour back" becomes a guardrail. If the panel keeps sanding things down (safer, greyer, more generic), stop and ask.
- **Report**: rounds, what changed and which reviewers asked for it, what was rejected and why, the final check, and an estimated cost. No scores.

## Step 7: the run log

Folder: `blind-climb-runs/YYYY-MM-DD-<slug>/` at the root of the user's project, unless their `AGENTS.md` names another place. Keep it outside the artifact being changed. It holds `run.md` (the setup from Step 1, round by round, decisions, rejected fixes), `run.json`, immutable snapshots, `round-N/round.json`, `round-N/labels.json`, `round-N/checks.json`, `round-N/<reviewer>.json`, `final-check/` and the screenshots. Reviewers never see this folder. Legacy logs without required metadata remain INCOMPLETE; do not fabricate data or rewrite historical audits during a skill update.

## Gotchas

- Reviewers asked "what's wrong" always find something. That's why the stop rule needs **no major** findings and **ready to ship** from everyone, not an empty list, and why the brief allows an empty list.
- Pairwise choices are noisy too: one reviewer's preference is not a decision. All declared reviewers and three distinct providers are required for a promotion or DONE.
- A candidate with many changes is hard to judge: keep each round's fixes few and focused, so a REVERT tells you which change hurt.
- Want a number after all (for a client report, or a target to beat)? Run a `hill-climb` Score on the final version.

## Make it yours

Keep personal settings in the user's `AGENTS.md` (or their agent's equivalent file), not in this file: council members, where run logs go, house rules that act as gates.
