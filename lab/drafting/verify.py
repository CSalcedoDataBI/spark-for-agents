"""Run every draft example on the pinned Spark and record what the engine really returns.

For each note in lab/drafting/out/*.json it adds:

- `actual`: the single cell as CAST(value AS STRING) prints it (`NULL` for null), or
  `ERROR: <error class or exception>: <first line>` when the query fails, or `SHAPE: ...` when
  it does not return exactly one row and one column.
- `verified`: true when `actual` matches `expected` (for an expected error, when the error
  class or exception the draft names appears in the actual error).
- `in_part`: true when `function` is one of the functions the draft's prompt was about.

A draft is a draft: nothing is promoted to a card unless `verified` is true and a person or
the experto has read the trap. Usage: python lab/drafting/verify.py [--spark 3.5.9]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
CHUNK = 22  # must match make_prompts.py


def parts(spark_version: str) -> dict[str, set[str]]:
    data = json.loads((ROOT / "exports" / f"spark-{spark_version}" / "sql-functions.json").read_text(encoding="utf-8"))
    groups: dict[str, list[str]] = defaultdict(list)
    for f in data["functions"]:
        groups[(f.get("info") or {}).get("group") or "ungrouped"].append(f["name"])
    out = {}
    for group, names in groups.items():
        for start in range(0, len(names), CHUNK):
            out[f"{group}-{start // CHUNK + 1}"] = set(names[start : start + CHUNK])
    return out


def run(spark, sql: str) -> str:
    try:
        width = spark._jsparkSession.sql(sql).schema().length()
        if width != 1:
            return f"SHAPE: {width} columns"
        # The cast runs in the engine: Python cannot even read some types (intervals), and an
        # auto-generated column name such as "round(-2.5, 0)" would parse as a nested field.
        rows = spark.sql(f"SELECT CAST(c AS STRING) FROM ({sql.strip().rstrip(';')}) AS t(c)").collect()
    except Exception as exc:  # the engine's verdict is the data here
        cls = getattr(exc, "getErrorClass", lambda: None)()
        lines = [line.strip() for line in str(exc).strip().splitlines() if line.strip()]
        # A Py4JJavaError's own first line says nothing; the Java exception is further down.
        cause = next((line for line in lines if "Exception:" in line or "Error:" in line), lines[0] if lines else "")
        return " ".join(part for part in ("ERROR:", type(exc).__name__, cls or "", "::", cause[:300]) if part)
    if len(rows) != 1:
        return f"SHAPE: {len(rows)} rows"
    value = rows[0][0]
    return "NULL" if value is None else value


def matches(expected: str, actual: str) -> bool:
    expected, actual = expected.strip(), actual.strip()
    if expected.startswith("ERROR"):
        if not actual.startswith("ERROR"):
            return False
        wanted = re.sub(r"^ERROR:\s*", "", expected).split(":")[0].strip()
        return not wanted or wanted.lower() in actual.lower()
    return expected == actual


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spark", default="3.5.9")
    args = parser.parse_args()

    import pyspark
    from pyspark.sql import SparkSession

    spark = (
        SparkSession.builder.master("local[1]")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("OFF")
    if spark.version != args.spark or pyspark.__version__ != args.spark:
        print(f"FAIL engine {spark.version} / pyspark {pyspark.__version__}, wanted {args.spark}", file=sys.stderr)
        return 1
    by_part = parts(args.spark)
    total = ok = 0
    try:
        for path in sorted((HERE / "out").glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            allowed = by_part.get(path.stem, set())
            for note in data.get("notes", []):
                note["actual"] = run(spark, note["example_sql"])
                note["verified"] = matches(note["expected"], note["actual"])
                note["in_part"] = note["function"] in allowed
                total += 1
                ok += note["verified"] and note["in_part"]
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    finally:
        spark.stop()
    print(f"OK {ok} of {total} notes verified on Spark {args.spark}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
