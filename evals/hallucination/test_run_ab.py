"""Tests for the invented-name A/B that make no API calls.

    python -m unittest evals.hallucination.test_run_ab
    python evals/hallucination/test_run_ab.py

They pin the metric (invented() flags a bogus F.* or SQL function and passes a real snippet),
assert every question's category is one the metric scores, and assert every documented trap is
genuinely absent from the Spark 3.5 catalogue -- so a name Spark later ships stops being a trap
loudly.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_ab  # noqa: E402


class Metric(unittest.TestCase):
    def test_valid_pyspark_snippet_has_no_inventions(self):
        text = "```python\ndf.select(F.regexp_extract(F.col(\"c\"), r\"(\\d+)\", 1))\n```"
        self.assertEqual(run_ab.invented(text), [])

    def test_bogus_F_function_flagged(self):
        self.assertTrue(run_ab.invented("```python\nF.totally_made_up_fn(F.col(\"x\"))\n```"))

    def test_bogus_sql_function_flagged(self):
        text = "```python\nspark.sql(\"SELECT made_up_sql_fn(x) FROM t\")\n```"
        self.assertTrue(run_ab.invented(text))

    def test_valid_sql_function_passes(self):
        text = "```python\nspark.sql(\"SELECT split_part(x, '-', 2) FROM t\")\n```"
        self.assertEqual(run_ab.invented(text), [])

    def test_prose_mention_not_counted(self):
        self.assertEqual(run_ab.invented("Use `F.coalesce`, not `F.first_non_null`."), [])


class Bank(unittest.TestCase):
    def setUp(self):
        self.questions = run_ab.load_questions()
        self.rows = run_ab.catalog_rows()

    def test_categories_are_scored_groups(self):
        for q in self.questions:
            self.assertIn(q["category"], ("functions", "sql-functions"), q["id"])
            self.assertIn(q["category"], self.rows, f"{q['id']}: bad category")

    def test_regimes_known(self):
        for q in self.questions:
            self.assertIn(q["regime"], ("core", "deep"), q["id"])

    def test_traps_are_absent_from_catalog(self):
        for q in self.questions:
            for trap in q.get("traps", []):
                if q["category"] == "functions":
                    code = f"```python\nF.{trap.split('.')[-1]}(x)\n```"
                else:
                    code = f"```python\nspark.sql(\"SELECT {trap}(x) FROM t\")\n```"
                self.assertTrue(run_ab.invented(code),
                                f"{q['id']}: trap {trap} is NOT flagged (shipped by Spark?)")


if __name__ == "__main__":
    unittest.main()
