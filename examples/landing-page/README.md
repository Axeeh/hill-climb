# Synthetic example

These files are made up: no landing page exists and no model wrote these answers. They show the shape of a run folder for `skills/hill-climb/scripts/aggregate.py`, and the tests use them.

```bash
python skills/hill-climb/scripts/aggregate.py examples/landing-page --target 9
```

Round 1 is a partial round, because one judge did not run. It stays `INCOMPLETE` and promotes nothing, so round 2 still compares against `snapshots/v0`.
