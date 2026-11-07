# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [2.0.0] - 2026-11-06

Run folders from earlier versions need a new run: `hill-climb` answers now use `ranking` instead of `comparison`.

### Changed

- `hill-climb` judges rank all the items instead of being told which two labels to compare, so the brief no longer points at the versions under development. The script reads the candidate-versus-incumbent preference from the ranking.
- The judge brief asks for evidence on every score below 10 instead of below 9, so it no longer reveals the default target.
- `--advisory` in both scripts applies to the latest assessment only; earlier decisions stand.
- A newer retained version makes an earlier `blind-climb` final check obsolete instead of `INVALID`. The next one goes in `final-check-2/`.
- `aggregate.py` regression and plateau warnings skip the rounds a judge did not run in, as the docs already said.
- Round 0 reports `BASELINE` in `aggregate.py`, matching `tally.py`.

### Fixed

- `aggregate.py` no longer dead-ends when round 0 fails a required check: round 0 is the starting point, and a passing candidate can replace it.
- `--advisory` no longer turns a run with several rounds into `INVALID`.
- Corrected two details attributed to the video: the 52–78% is total tokens, and the first scores were Opus 6.0 and Sol 6.5.

### Added

- How to check that every member can see the items, including T3 Code native attachments and their limit of 8 per message.
- `examples/landing-page/README.md`, which says the example is synthetic.

### Removed

- Rules duplicated between `CONTRIBUTING.md` and `AGENTS.md`, and exit codes repeated outside `run-format.md` and the script headers.

## [1.2.0] - 2026-11-06

### Added

- `references/run-format.md` in both `hill-climb` and `blind-climb`, documenting the run manifest (`run.json`), immutable snapshot lineage (`round.json`), and required programmatic check evidence (`checks.json`).
- `CONTRIBUTING.md` with pull request contribution rules and pre-PR checks.

### Changed

- Rename `blind-refine` to `blind-climb` across the skill folder, plugin manifest, docs, tests and CI.
- Harden `aggregate.py` and `tally.py` so missing manifests, missing required panel members, fewer than three distinct providers, failed or missing check evidence, or missing final checks report `INCOMPLETE` / `INVALID` instead of promoting a candidate or finishing a run.
- Add pairwise blind candidate-vs-incumbent selection to `hill-climb` Climb rounds alongside rubric scoring.
- Simplify the README install prompt to a single line and point agents to `AGENTS.md` at the bottom.

## [1.1.0] - 2026-11-05

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
