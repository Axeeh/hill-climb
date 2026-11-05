# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [1.1.0] - 2026-11-04

### Added

- `blind-refine` skill: an improvement loop with no scores. Fresh, blind reviewers pick between
  two versions in random order and list what's wrong by severity; the preferred version survives,
  and `scripts/tally.py` decides KEEP / REVERT and DONE / CONTINUE / PLATEAU. A final blind check
  compares the result with the original.
- `aggregate.py` reads an optional `rubric.json` and rejects category names that aren't in it.

### Changed

- Judges see the items only from a staging folder with neutral file names, never the run folder,
  so `labels.json` and earlier scores can't break the blindness.
- Council's "fix known issues before the audit" step is skipped in Score mode, and in Climb mode
  all changes happen in the fix step.
- Ratchet: go back only on a real regression (a judge's minimum falls by 0.5 or more, `--noise`)
  or a failed programmatic check; smaller drops are noise.
- Plateaus and regressions are computed per judge, only across rounds that judge ran in, so a
  stricter judge joining late no longer looks like a plateau.
- `aggregate.py` rejects two files for the same judge in one round.
- Shorter README with a simpler diagram: what it does, install, a few examples, credits.

## [1.0.1] - 2026-11-04

### Changed

- The hill-climb part is now public domain under the Unlicense, with no copyright holder.
  `skills/council/` keeps its MIT license from tstack.
- The README flow chart is a Mermaid diagram, so it renders aligned on GitHub.
- The README opens the install section with a "Tell your agent" message to paste into any agent,
  and its install examples are agent-neutral. AGENTS.md installs into the agent's own skills
  folder, with `.agents/skills/` as the shared default.

## [1.0.0] - 2026-11-04

### Added

- `hill-climb` skill: Score and Climb modes, blind judge brief, rubric presets for nine kinds
  of artifact, scorecard template, and `scripts/aggregate.py` to compute PASS / FAIL.
- `council` skill, vendored unchanged from [t3dotgg/tstack](https://github.com/t3dotgg/tstack)
  at commit `1085050`.
- Claude Code plugin marketplace manifest, example run, unit tests and CI.
