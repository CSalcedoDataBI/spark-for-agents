"""Export the Spark function catalogue from the engine itself.

Writes two JSON files under exports/spark-<version>/:

- sql-functions.json: every system function listed by `SHOW SYSTEM FUNCTIONS`, with the raw
  `DESCRIBE FUNCTION EXTENDED` lines and, when the built-in registry knows the function, the
  fields of its ExpressionInfo (group, since, arguments, examples, note, deprecated).
- pyspark-api.json: the public members of `pyspark.sql.functions`, `DataFrame` and `Column`,
  read by introspection of the installed package (signature, docstring, versionadded).

The output is deterministic (sorted, no timestamps), so CI can rerun the export and diff it
against the committed files. The script refuses to run when the JVM Spark and the `pyspark`
package disagree: a machine SPARK_HOME silently replaces the pinned engine.

Usage: python scripts/export_catalog.py [--out exports]
"""

from __future__ import annotations

import argparse
import inspect
import json
import platform
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Sphinx directives. At column 0 (after getdoc dedents) they describe the member itself; indented
# under a parameter they describe only that parameter, e.g. "Column as a parameter is deprecated".
VERSION_DIRECTIVE = re.compile(r"^([ \t]*)\.\. (versionadded|versionchanged|deprecated)::\s*([0-9.]+)", re.M)


def doc_versions(doc: str) -> tuple[dict, dict]:
    """(member versions, parameter versions), each {directive: [version, ...]} without repeats."""
    member: dict = {}
    parameter: dict = {}
    for indent, directive, version in VERSION_DIRECTIVE.findall(doc):
        target = parameter if indent else member
        versions = target.setdefault(directive, [])
        if version not in versions:
            versions.append(version)
    return member, parameter


def sql_functions(spark) -> list[dict]:
    jvm = spark._jvm
    registry = jvm.org.apache.spark.sql.catalyst.analysis.FunctionRegistry.builtin()
    identifier = jvm.org.apache.spark.sql.catalyst.FunctionIdentifier
    names = sorted({row[0] for row in spark.sql("SHOW SYSTEM FUNCTIONS").collect()})
    out = []
    for name in names:
        quoted = "`" + name.replace("`", "``") + "`"
        describe = [row[0] for row in spark.sql(f"DESCRIBE FUNCTION EXTENDED {quoted}").collect()]
        entry: dict = {"name": name, "describe": describe}
        found = registry.lookupFunction(identifier.apply(name))
        if found.isDefined():
            info = found.get()
            entry["info"] = {
                "class": info.getClassName(),
                "group": info.getGroup(),
                "since": info.getSince(),
                "source": info.getSource(),
                "usage": (info.getUsage() or "").strip(),
                "arguments": (info.getArguments() or "").strip(),
                "examples": (info.getExamples() or "").strip(),
                "note": (info.getNote() or "").strip(),
                "deprecated": (info.getDeprecated() or "").strip(),
            }
        out.append(entry)
    return out


def describe_member(owner: object, name: str) -> dict:
    member = inspect.getattr_static(owner, name)
    kind = "property" if isinstance(member, property) else "callable"
    target = member.fget if isinstance(member, property) else getattr(owner, name)
    try:
        signature = str(inspect.signature(target)) if kind == "callable" else None
    except (TypeError, ValueError):
        signature = None
    doc = inspect.getdoc(target) or ""
    versions, parameter_versions = doc_versions(doc)
    return {
        "name": name,
        "kind": kind,
        "signature": signature,
        "versions": versions,
        "parameter_versions": parameter_versions,
        "doc": doc,
    }


def pyspark_api() -> dict:
    from pyspark.sql import Column, DataFrame
    from pyspark.sql import functions as F

    functions = []
    for name in sorted(dir(F)):
        if name.startswith("_"):
            continue
        obj = getattr(F, name)
        # Only what the module defines: it also imports typing helpers, classes and modules.
        if inspect.isfunction(obj) and obj.__module__ == F.__name__:
            functions.append(describe_member(F, name))
    classes = {}
    for cls in (DataFrame, Column):
        classes[f"{cls.__module__}.{cls.__name__}"] = [
            describe_member(cls, name) for name in sorted(dir(cls)) if not name.startswith("_")
        ]
    return {"pyspark.sql.functions": functions, **classes}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=str(ROOT / "exports"))
    args = parser.parse_args()

    # Imported here so the tests can load doc_versions without pyspark installed.
    import pyspark
    from pyspark.sql import SparkSession

    spark = (
        SparkSession.builder.master("local[1]")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")
    try:
        if spark.version != pyspark.__version__:
            print(
                f"FAIL engine {spark.version} != pyspark {pyspark.__version__}: unset SPARK_HOME",
                file=sys.stderr,
            )
            return 1
        meta = {
            "spark": spark.version,
            "pyspark": pyspark.__version__,
            "python": ".".join(platform.python_version_tuple()[:2]),
            "source": "SHOW SYSTEM FUNCTIONS + DESCRIBE FUNCTION EXTENDED + FunctionRegistry.builtin",
        }
        sql = sql_functions(spark)
    finally:
        spark.stop()
    api = pyspark_api()

    folder = Path(args.out) / f"spark-{meta['spark']}"
    folder.mkdir(parents=True, exist_ok=True)
    write(folder / "sql-functions.json", {"meta": meta, "functions": sql})
    write(folder / "pyspark-api.json", {"meta": {**meta, "source": "inspect of pyspark"}, "modules": api})
    counts = ", ".join(f"{k}: {len(v)}" for k, v in api.items())
    print(f"OK spark {meta['spark']}: {len(sql)} SQL functions; {counts}")
    return 0


def write(path: Path, data: dict) -> None:
    text = json.dumps(data, indent=1, ensure_ascii=False, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    sys.exit(main())
