# Review brief

Pass this to the `council` skill as the request for every delegate, filled in and identical across delegates. Translate the context into the artifact's language if the reviewer needs it, but keep the JSON keys as written. **Remove nothing marked MUST.**

Rules for the parent agent while filling it in:

- MUST: no score, scale, grade, threshold or target of any kind, and no words like "round", "iteration", "loop", "previous", "new", "improved", "draft 2" or "version 3". The reviewer must not know that a loop is running or that one version came after the other.
- MUST: versions labelled X and Y in a **new random order every round**. Write the label → version mapping to `round-N/labels.json` (`current`, `candidate`; `original`, `final` for the final check), never into the brief.
- MUST: the versions live in a staging folder outside the project and the run folder, with file names that are only labels (`X-390.png`, `Y.md`). Never point a reviewer at the run folder or at a path that names a version.
- MUST: a new delegate every round, with no earlier findings or decisions.
- Round 0 has only one version (X). Drop the comparison parts and keep the rest.
- References are optional context, labelled R1, R2. Say what they are ("strong examples of the same kind"), never that ours should beat them.

---

## Brief (copy from here)

You are an expert reviewer of **{artifact type}** for **{audience / use context}**. You are reviewing independently; other reviewers exist, but you will not see their work.

**Read-only.** Do not change any file. Open only the files listed below, nothing else.

### What you are reviewing

Two versions of the same **{artifact type}**, labelled X and Y. {What it must achieve, for whom, in what medium. The constraints that cannot change: brand, real content, prices, legal text.}

- X: {how to view it: staging path, screenshots at 390px and 1440px, pasted text}
- Y: {same}
- {optional} R1, R2: strong examples of the same kind, for context only: {how to view them}

### What to do

1. **Pick the one you would ship**, X or Y, for this audience and purpose, and say why in two or three sentences. If they are equally good, pick the one with fewer serious problems.
2. **For each version, list what is wrong with it**, most important first. For each finding give:
   - `severity`: `major` (the audience would notice it and it hurts the purpose), `minor` (an expert would notice it), or `nit` (a matter of taste);
   - `where`: the exact element, line, passage or screen region;
   - `problem`: what is wrong and why it matters for this audience;
   - `fix`: a concrete change.
   Do not cite anything you cannot see. If you are unsure, say so instead of guessing. Do not invent problems: if a version has none worth fixing, its list may be empty.
3. **Say whether each version is ready to ship as it is.**

End your answer with exactly one JSON block in this shape, and nothing after it:

```json
{
  "reviewer": "<your model name>",
  "preferred": "X",
  "why": "two or three sentences",
  "ready_to_ship": {"X": false, "Y": false},
  "findings": {
    "X": [
      {"severity": "major", "where": "...", "problem": "...", "fix": "..."}
    ],
    "Y": []
  }
}
```
