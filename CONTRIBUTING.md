# Contributing

If you have changes or improvements to propose, open a pull request against `main`.

## Rules

- **Keep skills generic and portable.** Follow the [Agent Skills specification](https://agentskills.io/specification): `name` matches the folder name (lowercase, hyphens, ≤ 64 characters), `description` ≤ 1024 characters with clear trigger phrases, and relative file paths one level deep (`references/...`, `scripts/...`). Do not include personal names, client data, private paths or house rules.
- **Do not edit `skills/council/` directly.** It is vendored verbatim from [t3dotgg/tstack](https://github.com/t3dotgg/tstack) under the MIT license. If you are updating it to a newer upstream commit, copy `SKILL.md` and `LICENSE` unchanged and update the pinned commit hash in `AGENTS.md`, `.github/workflows/ci.yml` and `CHANGELOG.md`.
- **Standard library only for scripts.** `aggregate.py` and `tally.py` must run on Python 3.9+ using only the Python standard library and keep their exit codes stable. Update `tests/` (and `references/scorecard-template.md` for `aggregate.py`) whenever output or behavior changes.
- **No scores in `blind-climb`.** Its brief, script and PR table never ask for or display numeric ratings.
- **English everywhere.** Write docs, code, tests and commit messages in English (imperative subject line).
- **License.** Contributions to `hill-climb`, `blind-climb`, `tests/` and repo docs are released into the public domain under [The Unlicense](LICENSE), with no personal copyright lines.

## Checks to run before opening a PR

CI runs all of these on every pull request:

```bash
python -m unittest discover -s tests -v
python skills/hill-climb/scripts/aggregate.py examples/landing-page --target 9
pip install skills-ref && agentskills validate skills/hill-climb && agentskills validate skills/blind-climb && agentskills validate skills/council
python -m json.tool .claude-plugin/marketplace.json > /dev/null
```

See [AGENTS.md](AGENTS.md) for the full repository layout and release versioning rules.
