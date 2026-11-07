# Contributing

Open a pull request against `main`. [AGENTS.md](AGENTS.md) has the repository layout, the rules and the release steps; they apply to people too. Three of them matter most:

- `skills/council/` is copied unchanged from [tstack](https://github.com/t3dotgg/tstack), so don't edit it directly.
- The scripts use only the Python standard library and support 3.9+.
- `blind-climb` never asks for or shows a score.

Contributions to `hill-climb`, `blind-climb`, `tests/` and the docs are released under the [MIT license](LICENSE) of this repository, with no extra copyright lines.

CI runs these on every pull request:

```bash
python -m unittest discover -s tests -v
python skills/hill-climb/scripts/aggregate.py examples/landing-page --target 9
pip install skills-ref && agentskills validate skills/hill-climb && agentskills validate skills/blind-climb && agentskills validate skills/council
python -m json.tool .claude-plugin/marketplace.json > /dev/null
```
