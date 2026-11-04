# AGENTS.md

Guidance for coding agents working with this repository. People should start with [README.md](README.md).

This repo publishes two [Agent Skills](https://agentskills.io/specification):

- `skills/hill-climb/`: score an artifact with a blind multi-provider jury and improve it until it passes. Original work, public domain under the [Unlicense](LICENSE).
- `skills/council/`: the jury that `hill-climb` calls. It is a **verbatim** copy from [t3dotgg/tstack](https://github.com/t3dotgg/tstack) at commit `1085050f3baed1ac724caa4a8166145fb2ac88af`, MIT, Copyright (c) 2026 Theo Browne.

## If a user asked you to install these skills

1. **Install both skills.** `hill-climb` doesn't work without `council`.
2. **Ask about scope** if the user hasn't said: every project (user level) or only this one (project level).
3. **Use the first method that works:**
   - `npx skills add Axeeh/hill-climb` (add `-g` for user level). It needs Node.js 22.20+. Pick the agents the user works with.
   - Copy by hand: clone the repo and copy both folders under `skills/` into the folder you load skills from. If you don't have your own, use the shared one: `~/.agents/skills/` (user level) or `.agents/skills/` (project level).
   - If you run inside a host that drives agents from several providers (T3 Code, for example), install the skills where each of those agents can find them, so the jury works whichever agent the user picks.
4. **Don't overwrite a different `council`.** If one already exists and is byte-identical to `skills/council/SKILL.md`, skip it. If it differs, the user has customised it: ask before replacing it.
5. **Check prerequisites and report what's missing:** Python 3.9+ (`python --version`), and whether the agent can start subagents on models from three providers (in T3 Code, `orchestrator_capabilities`). Missing providers don't block the install, but runs will be marked as degraded.
6. **Offer to record their settings** in their own agent instructions file (`AGENTS.md` or its equivalent), never in the skill files: council members, default target, where run logs go.
7. Confirm by listing the installed folders. Run `python <skills-dir>/hill-climb/scripts/aggregate.py <repo>/examples/landing-page` if the repo is still cloned: it must print `RESULT: PASS`.

## If you are changing this repository

### Layout

```text
skills/hill-climb/SKILL.md            the procedure (keep it under 500 lines)
skills/hill-climb/references/         rubrics.md, judge-brief.md, scorecard-template.md
skills/hill-climb/scripts/aggregate.py
skills/hill-climb/agents/openai.yaml  Codex UI metadata
skills/council/                       vendored from tstack; never edit
examples/landing-page/                sample run, also used by the tests
tests/test_aggregate.py               standard-library unittest
.claude-plugin/marketplace.json       plugin marketplace manifest
```

### Rules

- **Never edit `skills/council/`.** To update it, copy `skills/council/SKILL.md` and `LICENSE` from a newer tstack commit, update the commit hash here, in `README.md`, in the CI workflow and in `CHANGELOG.md`. Then check that `hill-climb` Step 2 still matches what council does.
- **Follow the Agent Skills spec.** `name` matches the folder name (lowercase, hyphens, at most 64 characters). `description` is at most 1024 characters and says what the skill does and when to use it, with trigger phrases. File references are relative to the skill root and go one level deep (`references/x.md`, `scripts/x.py`).
- **Keep it generic.** No personal names, clients, private paths or house rules inside the skill. Personal settings belong in the user's `CLAUDE.md` or `AGENTS.md`, and the skill says so.
- **Credit Theo.** Keep the video link and the tstack credit in `SKILL.md` and `README.md`. A new idea from Theo gets credited the same way.
- **Quote exactly.** Numbers and quotes attributed to the video must match what is said in it. If you can't verify one, remove it.
- **The script uses only the standard library** and supports Python 3.9+. It keeps its exit codes stable: 0 PASS, 1 FAIL, 2 bad input. Any change to its output format must also update the README example, the scorecard template and the tests.
- **No personal names or copyright lines** for the hill-climb part: it is public domain under the Unlicense. Theo's copyright line in `skills/council/LICENSE` stays, because his MIT license requires it.
- **English everywhere** in this repo.
- **Versioning:** semver. A release bumps `metadata.version` in `skills/hill-climb/SKILL.md`, both `version` fields in `.claude-plugin/marketplace.json`, and adds a `CHANGELOG.md` entry.

### Check before you commit

```bash
python -m unittest discover -s tests -v
python skills/hill-climb/scripts/aggregate.py examples/landing-page --target 9   # RESULT: PASS
pip install skills-ref && agentskills validate skills/hill-climb && agentskills validate skills/council
python -m json.tool .claude-plugin/marketplace.json > /dev/null
```

CI (`.github/workflows/ci.yml`) runs the same checks. It also verifies that `skills/council/SKILL.md` still matches tstack at the pinned commit.

Commit messages are in English and imperative ("Add rubric preset for pitch decks").
