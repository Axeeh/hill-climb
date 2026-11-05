# Judge brief

Pass this to the `council` skill as the request for every delegate, filled in and identical across delegates. Translate the items into the artifact's language if the judge needs it, but keep the JSON keys as written. **Remove nothing marked MUST.**

Rules for the parent agent while filling it in:

- MUST: no target score, no threshold, no word like "goal", "iteration", "round", "loop" or "improve".
- MUST: items labelled A, B, C… in a **new random order every round**. Write the label → item mapping to `round-N/labels.json` (`"ours"` for our item, which `aggregate.py` reads) and to `run.md`, never into the brief.
- MUST: no hint about which item is ours. Strip our branding only if the references keep theirs. If branding is part of the judgement (a logo, a brand voice), leave every item's branding in and accept the bias.
- MUST: a new delegate every round, with no earlier scores or findings.
- MUST: the items live in a staging folder outside the project and the run folder, with file names that are only labels (`A-390.png`, `B.md`). Never point a judge at the run folder, at `labels.json` or at a path that names a product.
- Give the same context to everyone: the audience, the goal of the artifact, the medium (mobile Instagram feed, desktop app, client inbox).

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

For every score under 9.0, give concrete evidence: the exact element, line, passage or screen region, and why. Do not cite anything you cannot see. If you are unsure, say so instead of guessing.

Then list the **3 changes with the most impact** for each item, most important first.

End your answer with exactly one JSON block in this shape, and nothing after it:

```json
{
  "judge": "<your model name>",
  "items": {
    "A": {
      "scores": {"<category>": 7.5, "<category>": 8.0},
      "evidence": {"<category>": "why it is not a 9 or above, with location"},
      "top_fixes": ["...", "...", "..."]
    },
    "B": { "scores": {}, "evidence": {}, "top_fixes": [] }
  }
}
```

Category names in `scores` must match the rubric exactly.
