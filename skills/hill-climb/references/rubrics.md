# Rubric presets

Starting points, not laws: adapt them to the artifact (Step 1). Keep 4–7 categories. Each preset lists **gates** (programmatic checks: pass or fail, never scored by judges), **categories** with 6 / 8 / 10 anchors, **references** to look for, and **guardrails**.

House rules from the user's `AGENTS.md` or `CLAUDE.md` (accessibility baseline, brand palette, tone of voice, official price list) always apply as gates where relevant.

---

## 1. UI: site, app, dashboard

Based on the UI categories in Theo's video (hierarchy, typography, color and contrast, iconography). Show judges screenshots at **390px and 1440px**, light and dark if both exist, and the same screens for every item.

**Gates**: build passes, no console errors, axe with no serious issues, contrast, tap targets, no horizontal scroll, Lighthouse accessibility ≥ 95.

| Category | 6 | 8 | 10 |
|---|---|---|---|
| Hierarchy | Everything has the same weight; the eye doesn't know where to go | The main action and content are clear; secondary items mostly recede | The order of attention is obvious at a glance; every label recedes or leads on purpose |
| Typography | Fallback fonts, random sizes, cramped or overlong lines | A coherent scale, readable body, decent pairing | A deliberate scale and pairing, perfect rhythm, 65–75ch lines, truncation that keeps the part that matters |
| Color & contrast | Washed out or harsh, weak body contrast, color used without meaning | Readable in every mode, color mostly carries meaning | Color guides attention and state, comfortable in light and dark, never grayscale-bland |
| Layout & spacing | Inconsistent gaps, misalignment, crowding | A consistent spacing scale and a solid grid | Spacing creates grouping by itself; balanced density; mobile composed, not squeezed |
| Consistency | The same thing looks or is named differently across screens; mixed radii, borders, icons | Mostly one system, with a few strays | One system everywhere: radii, borders, indicators, labels, focus states |
| Iconography & detail | Mixed icon sets, unnecessary borders, generic placeholders | One icon set, clean details | Icons, states and micro-details feel crafted; nothing exists without a reason |
| Clarity of controls | Buttons don't look clickable; states are unclear | Controls are recognizable, with standard states | Every affordance is obvious; hover, focus, active and disabled are all designed |

**References**: the 2–3 best products in the same category. For a local business site, use the best competitor sites in its area and sector, plus one national best-in-class. For a portfolio, aim at award-level portfolios.
**Guardrails**: the brand palette and logo, the real content, the copy's language and tone, and technical constraints such as a CSP or self-hosted fonts.

## 2. Landing page: conversion

Use alongside preset 1 when the goal is leads or sales.

**Gates**: Lighthouse performance ≥ 90 on mobile, the form works end to end, the contact links (phone, chat, email) work, meta description and Open Graph tags are present.

| Category | 6 | 8 | 10 |
|---|---|---|---|
| Offer clarity (5 seconds) | You can't say what it is or who it's for | Clear after a scroll | What, for whom, where and why this one are clear above the fold on mobile |
| Trust | No proof, or generic stock photos | Real reviews or photos | Specific proof (real photos, names, numbers, local signals) right where doubt appears |
| Call to action | Hidden, vague or competing | Visible and repeated | One obvious next step, low effort, at every decision point |
| Friction | Long forms, slow, popups | Acceptable | Nothing stands between intent and contact |
| Distinctiveness | It looks like a template | Has its own character | Memorable; you couldn't swap the logo onto a competitor |

## 3. Cold outreach email

**Gates**: subject ≤ 50 characters, body ≤ 150 words, no jargon the reader wouldn't use, a single CTA, the real name of the business, no invented facts about the prospect.

| Category | 6 | 8 | 10 |
|---|---|---|---|
| Personalization | Could be sent to anyone | Mentions their business | One specific, verified observation about them that only they would recognize |
| Value in their words | Talks about us and our services | Talks about a problem of theirs | A concrete outcome for them (more calls, bookings), in their language |
| Brevity & readability | Walls of text | Short | Readable in 20 seconds on a phone, nothing to cut |
| Credibility | Salesy or generic claims | Polite and believable | Sounds like a real local person; a proof point without bragging |
| CTA | Vague or demanding | Clear | Low-commitment, easy to say yes to, one line |

**References**: the user's past emails that got a reply. If there are none, the best template they have.

## 4. Social post (carousel or single image)

Show judges the slides at real size in a mobile feed mockup, plus the caption.

**Gates**: real photos only (no stock unless agreed), the brand palette, readable text at feed size, ≤ 10 slides, the caption has a CTA.

| Category | 6 | 8 | 10 |
|---|---|---|---|
| Hook (slide 1) | Nobody would stop scrolling | Pleasant | A thumb-stopper that fits the brand |
| Visual quality | Amateur crops, clutter | Clean, on-brand | Magazine-level composition, consistent across slides |
| Flow | Slides are unrelated | A logical order | Each slide pulls you to the next; the CTA card feels earned |
| Copy | Generic or too long | Clear, informal | Specific, in the brand's voice, with one clear action |
| Brand fit | Could be any business | Recognizable | Unmistakably this brand |

**References**: the 2–3 best recent posts from competitors or category leaders, and the brand's best-performing post.

## 5. Quote or proposal

**Gates**: every price matches the official price list, totals add up, the required tax or legal wording is present, the client's name and details are correct, and it renders to PDF without breaks.

| Category | 6 | 8 | 10 |
|---|---|---|---|
| Clarity of offer | A list of technical items | Readable packages | The client understands what they get and why in one read, with no jargon |
| Perceived value | Price shown before value | Value explained | Outcomes framed before price; the price feels obvious |
| Easy decision | Too many options, unclear next step | Few options | 2–3 clear choices, a recommended one, a single next step |
| Trust | Bare | Professional | Proof, a clear scope, what is not included, terms that reassure |
| Look | A Word default | Tidy | As polished as the sites we sell |

## 6. Code or a PR

The jury is for what tests can't judge. **Always climb the programmatic score first.**

**Gates**: build, typecheck, lint, tests, and a performance or size budget if the goal is speed ("5× faster", "a quarter of the payload" are programmatic hills).

| Category | 6 | 8 | 10 |
|---|---|---|---|
| Correctness | Edge cases are missed | Main paths handled | Edge cases, errors and races handled and tested |
| Simplicity | Over-engineered or tangled | Reasonable | The obvious solution; nothing to remove |
| Fit with the codebase | Ignores existing patterns | Mostly follows them | Reads as if the same author wrote the whole repo |
| Readability | Hard to follow | Clear | Self-explanatory, with comments only where they add something |
| Risk | Breaking changes, no tests | Limited | Safe to merge, reversible, covered |

## 7. Prompt, skill, agent or tool description

Theo's second hill. **Build an eval set before anything else**: collect real cases where the agent did the wrong thing, group them, turn each into a test with an expected behaviour, and run it against the models you care about.

- **Phase 1**: climb to 100% on the eval set, and commit.
- **Phase 2**: cut size or tokens (for example by 2/3) while the eval stays at 100%. Revert any cut that drops a case.

A jury scores only what the eval can't: clarity to a newcomer, ambiguity, missing triggers.

| Category | 6 | 8 | 10 |
|---|---|---|---|
| Triggering | Fires on the wrong requests or misses the right ones | Mostly right | Exactly the right requests, with clear boundaries to neighbouring skills |
| Unambiguity | Steps can be read two ways | Clear | Only one possible reading |
| Economy | Repetition and filler | Lean | Every line changes behaviour |
| Robustness | Breaks on unusual input | Handles common cases | Says what to do when things go wrong |

## 8. Business plan, pitch or idea

This preset scores the document, not the business: check the facts separately.

**Gates**: every number has a source or is labelled as an assumption, the unit economics add up, and the market size is bottom-up.

| Category | 6 | 8 | 10 |
|---|---|---|---|
| Problem | Vague, or a solution looking for a problem | Real and described | Urgent, specific, with evidence of pain and willingness to pay |
| Solution & edge | Me-too | Some differentiation | A defensible reason this wins now |
| Market & go-to-market | Top-down TAM, no channel | A plausible channel | A first customer segment with a repeatable, costed channel |
| Economics | Missing or wishful | Plausible | CAC, LTV, churn and margin consistent and stress-tested |
| Risk & validation | Ignored | Listed | Biggest risks first, with cheap tests to kill or confirm them |

## 9. Any other text (bio, page copy, article)

**Gates**: length limits, language and tone rules, facts checked against the source.

| Category | 6 | 8 | 10 |
|---|---|---|---|
| Clarity | Needs rereading | Clear | Effortless; one idea per sentence |
| Specificity | Generic claims | Some detail | Concrete details only this subject has |
| Voice | Flat or off-brand | Consistent | Sounds exactly like the brand or the person |
| Structure | Wanders | Logical | Every paragraph earns its place; it scans |
| Purpose | It's unclear what the reader should do | Implied | The reader knows the next step and wants to take it |

---

## Building a new rubric

When nothing above fits:

1. Ask "what would make an expert say 10?" and write 4–7 answers that **don't overlap**. Each becomes a category.
2. Write the 6 / 8 / 10 anchors in observable terms ("the price is visible above the fold"), not taste words ("nice").
3. Move everything countable into gates.
4. Find at least one reference that would score high, and test the rubric on it once before the run: if the reference scores 6, the rubric is wrong.
5. Save a rubric that worked as a new preset here.
