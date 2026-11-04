---
name: hill-climb
description: Score any artifact against a rubric with a blind, multi-provider jury (programmatic checks first, then the council skill as judges) and, when asked, keep improving it round after round until every judge rates every category at or above a target and above best-in-class references. Works for UIs and websites, landing pages, emails, social posts, proposals, code, prompts and skills, business plans and other writing. Use when the user says "hill climb", "score this", "rate this out of 10", "get this to a 9/10", "keep improving until the judges agree", "make it better than [competitor]", "scorecard" or "build an eval for this". Not for a one-off second opinion with no rubric or loop; use council directly for that.
license: Unlicense
compatibility: Needs the council skill (bundled in this repo), an agent that can run subagents on models from other providers (T3 Code delegate_task or an equivalent harness), and Python 3.9+ for scripts/aggregate.py.
metadata:
  author: Axeeh
  version: "1.0.1"
  source: https://github.com/Axeeh/hill-climb
---

# Hill climb

Method from Theo Browne's video "Agents Sucked At UI (Until Today)" (https://youtu.be/xq0eB8vxeqk, 2026-11-03). An agent improves anything you can score, as long as the score is honest. Theo took T3 Code's UI from 6/10 to 10/10 from every judge. With the same approach he cut the tokens in its tool descriptions by 52–78% while keeping a perfect eval score. This skill turns his loop into a procedure for any field.

**The idea in one line:** turn the goal into a number, let blind judges produce it, fix what they agree on, repeat until it passes, and keep the best version at every step.

## Two modes

- **Score** ("score this", "rate it"): one round. Build the rubric, run the jury, deliver a scorecard. Change nothing.
- **Climb** ("get it to a 9", "keep improving"): the full loop below. It changes the artifact, so it needs a safe place to work: a branch or worktree for code, a numbered copy (`v2`, `v3`) for documents. Never climb on the only copy of something.

If the request doesn't say which, ask once. The default is Score.

## Step 1: define the hill (before any judging)

Write these down in the run log (Step 7). Before a Climb, show the user a 5-line summary and get an OK.

1. **Artifact**: exactly what is scored and how judges will see it (screenshots at mobile and desktop width, the text, the diff, the PDF).
2. **Programmatic checks first.** Anything a program can measure is a program, not an opinion: build, tests, Lighthouse, axe, contrast ratios, word count, file size, token count, an eval set of real failure cases. Theo's rule: "if you can take a problem you have and turn it into a program that gives a score, your agents are going to make that score go up." Programmatic checks are **gates**: a failure blocks a pass whatever the judges say. If the whole goal is measurable, skip the jury and climb the program.
3. **Rubric**: 4–7 categories, each with a one-line description of what a 6, an 8 and a 10 look like. Start from [references/rubrics.md](references/rubrics.md) and adapt it. Never let judges invent their own categories.
4. **References**: 1–3 best-in-class examples of the same kind (a competitor's product, the best email the user ever sent, the category leader). **This is the most important lever in the method.** Judged alone, T3 Code's UI went "from 6 to 9"; next to Claude Code and Codex the same version scored 7.4. With no reference the score inflates. If no reference exists, say that the scores are absolute and trust them less.
5. **Target**: by default **≥ 9.0 in every category from every gating judge, and ≥ the best reference in every category**. The user may set another bar.
6. **Budget**: maximum rounds (default 5 for a Climb) and a rough cost limit. In the video, going from 9 to 9.5 took 10 extra rounds, so say this when the target is above 9.
7. **Guardrails**: what must not get worse (brand identity, real content, prices, legal text, accessibility, the agreed scope). Fight scope creep, because judges keep asking for more.

## Step 2: the jury is the `council` skill

Don't build a jury here: **every round of judging is one run of the `council` skill**. Read its `SKILL.md` and follow it for everything it owns: which models (the members named in the user's `CLAUDE.md` or `AGENTS.md`, otherwise the latest flagship of each of three providers), how to start them, read-only delegates, reporting an unreachable member instead of substituting it, round counting and the PR table.

Hill-climb adds a frame around council. Where the two differ, these rules win during a climb:

- **One council run = one round.** Council's own loop ("continue until all delegates are satisfied") doesn't apply here. Step 4 decides whether there is another round, and Step 5 does the fixing. Each new round is a new council run with **new delegates**, never a follow-up message in an earlier delegate's thread.
- **The delegates' request is the judge brief** ([references/judge-brief.md](references/judge-brief.md)), identical for each member, not a free-form review request.
- **Keep the raw answers.** Besides council's summary, save each delegate's JSON block untouched as `round-N/<judge>.json`. The score comes from the script in Step 4, never from the summary.
- **Gated order saves cost and time.** Council lets the request name its members, so name only the fastest and cheapest member until it passes, then add the next and slower one, and finally the third. Members left out of a round are `not run`. A slow member never blocks the loop, but every member must pass in the **same final round**.
- **Advisory members.** A member that cites evidence that isn't there (wrong line numbers, a passage that doesn't exist, a finding already fixed) becomes advisory. Log its findings, drop its score from the gate (`--advisory` in Step 4), and say so in the scorecard.
- If council can't reach three providers, the run is degraded: judges from one provider share the same blind spots. Say so in the scorecard.

## Step 3: what council receives (blind, fresh, read-only)

Fill in [references/judge-brief.md](references/judge-brief.md) and pass it to council as the delegates' brief. These rules matter more than the wording:

- **Blind to the target.** Never tell a judge the threshold, the goal or that a loop is running. Theo suspects that writing "I want 9.5" pushed the scores.
- **Blind to authorship.** Label the items A, B, C, shuffle their order every round, and don't say which one is ours.
- **Fresh context every round**: a new delegate each round, never a follow-up in the same thread, and no earlier scores.
- **Re-score the references every round, in the same call.** Reference scores drift too: Claude Code went from 8.3 to 9.1 with identical screenshots. The gap to the reference is the stable signal, not the raw number.
- **Read-only**: judges look and score, and the parent agent makes every change.
- Ask for a score from 1 to 10 with one decimal per item and category, the evidence for every point under 9, and the 3 fixes with the most impact. The output is the JSON block in the brief.

## Step 4: aggregate and decide

Save each judge's JSON in the run folder, then run the bundled script from this skill's folder:

```bash
python scripts/aggregate.py <run-folder> --target 9 [--advisory "<judge name>"]
```

It prints the round table, each category's minimum across judges, the gap to the best reference and `RESULT: PASS` or `RESULT: FAIL` (exit code 0 or 1). Read it with these rules:

- **Noise**: the same input to the same model gives different scores. Treat a difference under 0.5 as noise. A 9+ from several providers at once is meaningful; a 9 from a single judge is not.
- **The gate is the strictest gating judge**, not the average.
- **Stop** on PASS, on budget, or on a **plateau**: two rounds in a row where the minimum score doesn't rise by at least 0.3. On a plateau, stop and report the blocking category instead of burning more rounds.

## Step 5: fix (Climb only)

1. **Choose what to fix**: first anything two or more judges flag, then the lowest category. A fix only one judge wants waits unless it is clearly right. Reject anything that breaks a guardrail or expands scope, and note why.
2. Apply the fixes, then run the programmatic checks again (build, tests, render). For anything visual, look at it yourself after every change, at mobile width first.
3. **Ratchet**: if the next round scores lower, go back to the best version and try different fixes. Theo's eval fell from 66 to 63 out of 85 after one change. Keep the best version safe with a commit per improving round, or a numbered copy.
4. Start a new round from Step 3: a new council run, with new delegates.

## Step 6: human checkpoints

- After each improving round, show the user **before and after side by side, with the changes annotated** (arrows or notes on what changed and why). Theo couldn't see the difference until he asked for annotated diagrams.
- The user's taste beats the jury. If they say something like "too grey, bring the colour back", add it as a guardrail or a rubric line and keep climbing. Over-optimising for judges makes things bland.
- **After a PASS**, offer to raise the bar (9 → 9.5 → 10) **on a separate branch or copy**, so the version that passed stays shippable.
- **Two-phase climb** for "better and smaller or cheaper": first reach a perfect quality score and lock it with a commit or copy. Then optimise the second goal (length, tokens, cost, load time) while the quality score must stay perfect. Example: "make it a third of the size and still score 100%".

## Step 7: the run log and the scorecard

- Folder: `hill-climb-runs/YYYY-MM-DD-<slug>/` at the root of the user's project, unless their `AGENTS.md` or `CLAUDE.md` names another place. Keep it outside the artifact being changed. It holds `run.md` (the hill from Step 1, round by round, decisions and rejected fixes), `round-N/labels.json`, `round-N/<judge>.json` and the screenshots.
- At the end, write `scorecard.md` from [references/scorecard-template.md](references/scorecard-template.md), in the user's language: the round table per judge, the final category table against the references, what changed, the stop reason, advisory or missing judges, rounds, time and an estimated cost.
- If the work is a PR, council's PR rule applies. Its `## Council review` table goes in the PR description, with each cell holding that member's **minimum category score** for the round from `aggregate.py`. Members left out by the gated order are `not run`. Never invent a score; write `no score` instead.

## Gotchas

- Judges start from different baselines (Opus 6.0 vs Sol 7.0 on the same screen). Compare each judge with itself across rounds, never across judges.
- A judge that ran out of usage is `not run` for that round, not a pass.
- When the jury converges on blandness (too grey, too safe, too generic), that is the cue for a human checkpoint, not one more round.
- Climbing costs real money: Theo spent about $250 on the runs he showed. Report the rounds and an estimated cost before you raise the bar.

## Make it yours

Put personal settings in the user's `CLAUDE.md` or `AGENTS.md`, not in this file, so the skill can be updated without losing them: council members, the default target, where run logs go, house rules that act as gates (brand palette, tone, price list). A rubric that worked well belongs in [references/rubrics.md](references/rubrics.md) as a new preset.
