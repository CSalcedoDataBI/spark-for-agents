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

## Not in scope

- Running Spark jobs or managing Fabric items. That is `fabric-cli` and the Fabric skills.
- ETL design, Delta table layout and medallion patterns. That is
  [etl-blueprints-for-agents](https://github.com/CSalcedoDataBI/etl-blueprints-for-agents).

## License

[MIT](LICENSE).
