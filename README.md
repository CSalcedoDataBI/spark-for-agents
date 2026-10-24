# spark-for-agents

> **Pre-release.** This repository is public from day one, but nothing in it is ready to install
> yet. The function catalogue has not been generated, and there is no plugin to add. Watch the
> repository or follow the [v0.1 epic](https://github.com/CSalcedoDataBI/spark-for-agents/issues/2)
> if you want to know when that changes.

The Apache Spark reference for AI agents: PySpark and Spark SQL, with every built-in function
**exported from the engine itself** instead of typed from memory. Each one comes with its signature,
the Spark version that introduced it, whether the Microsoft Fabric runtime has it, and the gotchas
the documentation leaves out.

It is the sibling of [dax-for-agents](https://github.com/CSalcedoDataBI/dax-for-agents) and
[powerquery-m-for-agents](https://github.com/CSalcedoDataBI/powerquery-m-for-agents), and it
follows the same rule: **an agent never reads a function name that did not come from the engine.**

## What it will contain

| Piece | Source | Status |
|---|---|---|
| Function cards (Spark SQL built-ins) | `SHOW FUNCTIONS` + `DESCRIBE FUNCTION EXTENDED`, run on a real Spark | planned |
| PySpark API cards (`pyspark.sql.functions`, `DataFrame`) | introspection of the installed `pyspark` package | planned |
| Fabric runtime availability | the same export, run on each Fabric Spark runtime | planned |
| Traps and executed examples | notes written by hand, each example run and its result saved | planned |
| `spark-feedback` skill | report a wrong or missing card as a public issue | planned |

## Does the reference stop invented names?

That is the whole reason this repository exists, so it is measured, not asserted. Each question
in the [bank](evals/hallucination/questions.yaml) is asked twice of the same model: once alone
(arm A), and once with the catalogue rows of its category (arm B — names and one-line summaries,
never the card that holds the answer). The surface a Spark agent invents on is the **function
name**, so every `F.<name>` and every function inside a `spark.sql(...)` string an answer writes
**in runnable code** is looked up against the exported PySpark functions (422) and Spark SQL
functions (438) — the same catalogue CI enforces ([`scripts/check_repo.py`](scripts/check_repo.py)).
No model judges another, and any saved run recounts for free with `--replay`.

| Model | Questions compared | Invented, without the reference | Invented, with it |
|---|---|---|---|
| Claude Haiku 5.5 | 15 | 0 | 0 |
| Claude Haiku 4.5 | 15 | 0 | 0 |

The honest reading: on this bank, neither current Claude model invents a Spark function name — they
reach for `F.regexp_extract`, `F.percentile_approx`, `F.months_between`, `split_part` and the rest
correctly, with the reference or without it. Spark's function surface is large and
well-represented in training. The value here is the **measurement that keeps working**: 437 SQL
functions and 422 PySpark functions are a wide field to invent in, and this will show the gap the
day a cheaper or older model is put behind an agent, or catch a regression as the catalogue grows.

```bash
python evals/hallucination/run_ab.py --model claude-haiku-5-5 --out run.json
python evals/hallucination/run_ab.py --replay evals/hallucination/runs/2026-10-23-claude-haiku-5-5.json
python evals/hallucination/test_run_ab.py
```

Raw answers for every run are in [`evals/hallucination/runs/`](evals/hallucination/runs/). The eval
calls the Anthropic or DeepSeek API with `ANTHROPIC_API_KEY` or `DEEPSEEK_API_KEY` read from the
environment (never from the command line, never written into the run file); `--replay` sends
nothing.

## Not in scope

- Running Spark jobs or managing Fabric items. That is `fabric-cli` and the Fabric skills.
- ETL design, Delta table layout and medallion patterns. That is
  [etl-blueprints-for-agents](https://github.com/CSalcedoDataBI/etl-blueprints-for-agents).

## License

[MIT](LICENSE).
