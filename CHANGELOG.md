# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed

- Shorter README without the diagram: what it does, install, two examples, credits.

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
