# Contributing

## Report a bug or a wrong function

Open an [issue](https://github.com/CSalcedoDataBI/spark-for-agents/issues/new). For a function that
is wrong, missing or catalogued under the wrong version, include:

- the Spark version and where you ran it (local `pyspark`, a Fabric runtime, another platform);
- the function name and what the catalogue says about it;
- the query you ran and what the engine returned.

## Changes go through a pull request

Every change to `main` comes in through a pull request, and the required `Validate` check must pass
before it can merge. Run the same checks locally first:

```bash
python scripts/check_repo.py
python -m unittest discover -s tests
```

## No name outside the exported catalogue

The catalogue under `exports/` is exported from the engine by `scripts/export_catalog.py`, never
typed by hand. Anything an agent reads may only name functions that are in it, and `Validate` fails
otherwise. If a function is missing, the fix is a new export, not a hand edit.

## License

By contributing, you agree that your contribution is licensed under the [MIT License](LICENSE).
