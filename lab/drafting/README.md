# Drafting

Drafts of traps and examples for the Spark SQL functions, written by a model and checked by the
engine. Nothing here is a card yet: a note is promoted by PR only when `verified` and `in_part`
are true and someone has read the trap.

1. `python lab/drafting/make_prompts.py` builds one prompt per chunk of a function group from
   `exports/spark-<v>/sql-functions.json` into `prompts/` (git-ignored).
2. Each prompt goes to `claude-review --prompt-file prompts/<part>.md --schema schema.json -o out/<part>.json`.
3. `python lab/drafting/verify.py` runs every `example_sql` on the pinned Spark (UTC session) and
   writes `actual`, `verified` and `in_part` into each note. It needs the `pyspark` of
   `requirements-export.txt` and no machine `SPARK_HOME` pointing elsewhere.
4. `python scripts/check_repo.py` (the `Validate` check) fails on any `function`, or any call
   written in backticks, that is not in the exported catalogue.
