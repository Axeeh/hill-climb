# Scorecard template

Write `scorecard.md` from this skeleton, in the user's language. Paste the tables from `aggregate.py`. Replace every `{…}`; a judge that didn't run is `not run`, a judge that gave no score is `no score`.

```markdown
# Scorecard: {what was scored}

**Date:** {YYYY-MM-DD} · **Mode:** {Score | Climb} · **Result:** {PASS | FAIL | stopped on plateau | stopped on budget}

## Summary

{3–5 lines: starting score → final score, against which references, what made the difference, what still blocks.}

## The hill

- **Artifact:** {what, and how the judges saw it}
- **References:** {1–3 best-in-class examples}
- **Target:** {e.g. ≥ 9.0 in every category from every judge, and ≥ the best reference}
- **Programmatic checks:** {list, with final result}
- **Guardrails:** {what must not get worse}
- **Jury:** {council members, order they joined, advisory members and why}

## Minimum score per round (ours)

| Judge | Round 0 | Round 1 | Round 2 | … |
|---|---|---|---|---|
| Claude Opus | 6.0 | 7.5 | 9.0 | |
| GPT Sol | 6.5 | 8.0 | 9.2 | |
| Gemini Argon | not run | not run | 9.0 | |

## Categories, final round

| Category | Ours (lowest judge) | Best reference (lowest judge) | Smallest per-judge gap |
|---|---|---|---|
| {…} | | | |

## What changed

{Per round: change → why (which judges asked for it). Links to the annotated before/after screenshots.}

## Rejected

{Judge suggestions not applied, and why: out of scope, broke a guardrail, only one judge, the user's taste.}

## Cost

Rounds: {N} · Agent time: {hours} · Estimated cost: {amount, or "covered by subscriptions"}

## Next step

{Merge or deliver, raise the bar on a separate branch, or the category to unblock.}
```
