---
name: blind-refine
description: Improve any artifact round after round with a blind, multi-provider review panel (the council skill) that never sees a score, a target or a loop. Each round fresh reviewers get two unlabelled versions in random order, pick the one they would ship, and list what is wrong with each by severity; the better version survives and the agreed findings are fixed. Stops when no reviewer finds anything major and all would ship it, on a plateau or on budget, then checks the final version blindly against the original. Works for UIs and websites, emails, social posts, proposals, code, prompts and skills, business plans and other writing. Use when the user says "refine this", "improve it without scores", "keep improving until the reviewers have nothing left", "blind review loop", "make it better, no grades" or worries that numbers bias the reviewers. Not for a scorecard or a number to beat (use hill-climb), or for a one-off second opinion (use council).
license: Unlicense
compatibility: Needs the council skill (bundled in this repo), an agent that can run subagents on models from other providers (T3 Code delegate_task or an equivalent harness), and Python 3.9+ for scripts/tally.py.
metadata:
  author: Axeeh
  version: "1.1.0"
  source: https://github.com/Axeeh/hill-climb
---

# Blind refine

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

## Step 2: the panel is the `council` skill

**Every round of review is one run of the `council` skill.** Read its `SKILL.md` and follow it for which models (the members named in the user's `AGENTS.md` or equivalent, otherwise the latest flagship of three providers), how to start them, read-only delegates and reporting an unreachable member instead of substituting it.

Where the two differ, these rules win:

- **No fixing inside council.** Council fixes known issues before it audits; here all changes happen in Step 5, so each round reviews fixed versions.
- **One council run = one round**, with **new delegates** every round. Council's "continue until all delegates are satisfied" loop is replaced by Steps 4–6.
- **The delegates' request is the review brief** ([references/review-brief.md](references/review-brief.md)), identical for each member.
- **Keep the raw answers**: save each delegate's JSON block untouched as `round-N/<reviewer>.json`. Decisions come from the script in Step 4, never from council's summary.
- **No scores, anywhere.** Council asks for a score out of 10 on code reviews: don't, not even "for the PR table". If the work ends in a PR, its `## Council review` table lists each member's choice and major findings per round (`kept candidate, 0 major`), never a number.
- If council can't reach three providers, say the run is degraded in the summary.

## Step 3: blind, fresh, read-only

These rules matter more than the wording of the brief:

- **No numbers and no loop.** Never mention a score, a target, a round, a previous version or an improvement. The brief only asks which version to ship and what is wrong.
- **Blind to order.** Label the two versions X and Y in a new random order every round. Never say which one is newer or which one the agent wrote.
- **Blind files.** Copy each version into a new staging folder **outside the project and the run folder** (the system temp folder), named only by label: `X-390.png`, `Y-1440.png`, `X.md`. Tell reviewers to open nothing else. The run folder holds `labels.json` and earlier findings, so a reviewer that reads it is no longer blind. For code that only exists in the project, give each version as a copied file or excerpt, not a path into the repo.
- **Fresh context**: a new delegate every round, never a follow-up in an old thread, and no earlier findings.
- **Read-only**: reviewers look and report; the parent agent makes every change.

## Step 4: tally and decide

Save each reviewer's JSON and `labels.json` (`{"X": "candidate", "Y": "current"}`, shuffled), then run the bundled script from this skill's folder:

```bash
python scripts/tally.py <run-folder> [--advisory "<reviewer name>"]
```

It prints which version survived each round, the findings on the kept version per reviewer, and a result:

- **KEEP or REVERT**: the candidate survives only if **more than half** of the gating reviewers prefer it. A tie keeps the current version.
- **DONE** (exit 0): on the kept version, no gating reviewer reports a `major` finding and every gating reviewer would ship it. Go to Step 6.
- **CONTINUE** (exit 1): fix and run another round.
- **PLATEAU** (exit 3): the candidate lost two rounds in a row. Stop and report what keeps failing instead of burning rounds.

A reviewer that cites things that aren't there (wrong lines, a passage that doesn't exist, a problem already fixed) becomes advisory: pass `--advisory` and say so in the summary.

## Step 5: fix

1. **Choose what to fix**, from the findings on the kept version: first the `major` findings two or more reviewers agree on, then any other `major`, then `minor` findings two or more reviewers share. A finding only one reviewer has waits unless it is clearly right. `nit`s are taste: skip them unless the user cares. Reject anything that breaks a guardrail or grows the scope, and note why.
2. Apply the fixes to a copy of the kept version: that is the next **candidate**. If you hand the fixing to a subagent, give it the findings and the context from Step 1, never a score or a target, for the same reason as the reviewers.
3. Run the programmatic checks. For anything visual, look at it yourself, at mobile width first.
4. Start the next round from Step 3: the kept version is `current`, the fix is `candidate`.

Round 0 has only the starting version: reviewers list its problems, the first fix becomes the first candidate.

## Step 6: finish

- **Final check.** After DONE, a plateau or the budget, run one more council run with the **original** and the **final** version as X and Y, blind, in a `final-check/` folder (`{"X": "final", "Y": "original"}`, shuffled). Small steps can each win and still drift somewhere worse. If the reviewers don't prefer the final version, `tally.py` warns: show the user both and let them decide.
- **Human checkpoints.** After a kept candidate, show the user before and after side by side with the changes annotated. The user's taste beats the panel: a correction like "too grey, bring the colour back" becomes a guardrail. If the panel keeps sanding things down (safer, greyer, more generic), stop and ask.
- **Report**: rounds, what changed and which reviewers asked for it, what was rejected and why, the final check, and an estimated cost. No scores.

## Step 7: the run log

Folder: `blind-refine-runs/YYYY-MM-DD-<slug>/` at the root of the user's project, unless their `AGENTS.md` names another place. Keep it outside the artifact being changed. It holds `run.md` (the setup from Step 1, round by round, decisions, rejected fixes), `round-N/labels.json`, `round-N/<reviewer>.json`, `final-check/` and the screenshots. Reviewers never see this folder.

## Gotchas

- Reviewers asked "what's wrong" always find something. That's why the stop rule needs **no major** findings and **ready to ship** from everyone, not an empty list, and why the brief allows an empty list.
- Pairwise choices are noisy too: one reviewer's preference is not a decision. With fewer than two gating reviewers, `tally.py` warns.
- A candidate with many changes is hard to judge: keep each round's fixes few and focused, so a REVERT tells you which change hurt.
- Want a number after all (for a client report, or a target to beat)? Run a `hill-climb` Score on the final version.

## Make it yours

Keep personal settings in the user's `AGENTS.md` (or their agent's equivalent file), not in this file: council members, where run logs go, house rules that act as gates.
