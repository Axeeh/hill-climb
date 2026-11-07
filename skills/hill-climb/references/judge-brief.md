# Judge brief

Pass this to the `council` skill as the request for every delegate, filled in and identical across delegates. Translate the items into the artifact's language if the judge needs it, but keep the JSON keys as written. **Remove nothing marked MUST.**

Rules for the parent agent while filling it in:

- MUST: no target score, no threshold, no word like "goal", "iteration", "round", "loop", "previous" or "improve".
- MUST: items labelled A, B, C… in a **new random order every round**. Write the label → item mapping to `round-N/labels.json` (`"ours"` for our item, which `aggregate.py` reads) and to `run.md`, never into the brief.
- MUST: no hint about which item is ours. Strip our branding only if the references keep theirs. If branding is part of the judgement (a logo, a brand voice), leave every item's branding in and accept the bias.
- MUST: a new delegate every round, with no earlier scores or findings.
- MUST: the items live in a staging folder outside the project and the run folder, with file names that are only labels (`A-390.png`, `B.md`). Never point a judge at the run folder, at `labels.json` or at a path that names a product.
- MUST: after the Climb baseline, include the candidate and the best retained snapshot among the items. Privately map them as `ours` and `incumbent`, with snapshot IDs in `round.json`. The brief stays the same in every round and never points at those two items: every judge ranks all the items, and the script reads the preference from the ranking.
- MUST: `judge` in the answer must match the model name assigned in `run.json`. Supply that reviewer's own name when dispatching; the artifact context, rubric and comparison instructions remain identical for all members.
- Give the same context to everyone: the audience, what the artifact must achieve, the medium (mobile Instagram feed, desktop app, client inbox).

---

## Brief (copy from here)

You are an expert reviewer of **{artifact type}** for **{audience / use context}**. You are reviewing independently; other reviewers exist, but you will not see their work.

**Read-only.** Do not change any file. Open only the files listed below, nothing else. Look, evaluate and report.

### What you are reviewing

{N} items, labelled {A, B, C…}. They are different versions or different products of the same kind. Evaluate each one on its own merits and against the others.

{for each item: label, how to view it (path to screenshots at 390px and 1440px, file path, pasted text, URL)}

### Rubric

Score every item in every category from 1.0 to 10.0, with one decimal. Use the anchors, and the whole scale: a 10 means you would not change anything, and a 6 means clearly amateur.

| Category | 6 looks like | 8 looks like | 10 looks like |
|---|---|---|---|
{rows from the preset in rubrics.md, adapted}

### What to return

For every score below 10, give concrete evidence: the exact element, line, passage or screen region, and why. Do not cite anything you cannot see. If you are unsure, say so instead of guessing.

Then list the **3 changes with the most impact** for each item, most important first.

Finally, rank all the items from the one you would ship first to the one you would ship last for this audience and task, and give concrete evidence for the order. Put items in the same group only if neither has a justified advantage. Judge the actual task outcome; do not guess who made an item or when.

End your answer with exactly one JSON block in this shape, and nothing after it:

```json
{
  "judge": "<assigned model name, exactly>",
  "items": {
    "A": {
      "scores": {"<category>": 7.5, "<category>": 8.0},
      "evidence": {"<category>": "what keeps it from a 10, with location"},
      "top_fixes": ["...", "...", "..."]
    },
    "B": { "scores": {}, "evidence": {}, "top_fixes": [] }
  },
  "ranking": {"order": [["B"], ["A", "C"]], "reason": "Specific evidence for the order"}
}
```

Category names in `scores` must match the rubric exactly.
Score every listed item in every category. Return scores as JSON numbers from 1.0 to 10.0, never numeric strings. `order` lists every item once, best first; a group holds items you consider equal.
