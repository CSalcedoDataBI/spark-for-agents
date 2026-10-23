"""Tests for scripts/check_repo.py. Run with: python -m unittest discover -s tests

The fixtures use a made-up catalogue (fixture_fn, Fixture_Method) on purpose: this repo never
writes a real Spark function name that did not come from an export.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import check_repo  # noqa: E402


def make_repo(root: Path, catalogue: bool = True) -> None:
    if catalogue:
        export = root / "exports" / "spark-0.0.0"
        export.mkdir(parents=True)
        (export / "sql-functions.json").write_text(
            json.dumps({"meta": {}, "functions": [{"name": "fixture_fn", "describe": []}]}), encoding="utf-8"
        )
        (export / "pyspark-api.json").write_text(
            json.dumps({"meta": {}, "modules": {"m": [{"name": "Fixture_Method"}]}}), encoding="utf-8"
        )
    (root / "skills" / "s").mkdir(parents=True)


class CheckNamesTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write_skill(self, text: str) -> None:
        (self.root / "skills" / "s" / "SKILL.md").write_text(text, encoding="utf-8")

    def test_known_names_pass_sql_case_insensitive(self) -> None:
        make_repo(self.root)
        self.write_skill("Use `FIXTURE_FN(x)`, `F.Fixture_Method(c)` and `df.Fixture_Method()`.")
        self.assertEqual(check_repo.check_names(self.root), [])

    def test_invented_call_fails(self) -> None:
        make_repo(self.root)
        self.write_skill("Use `invented_fn(x)` here.")
        errors = check_repo.check_names(self.root)
        self.assertEqual(len(errors), 1)
        self.assertIn("invented_fn", errors[0])

    def test_pyspark_names_are_case_sensitive(self) -> None:
        make_repo(self.root)
        self.write_skill("Use `F.fixture_method(c)`.")
        self.assertEqual(len(check_repo.check_names(self.root)), 1)

    def test_plain_code_spans_are_not_calls(self) -> None:
        make_repo(self.root)
        self.write_skill("A column named `invented_fn` and a path `a/b.json`.")
        self.assertEqual(check_repo.check_names(self.root), [])

    def test_draft_function_field_is_checked(self) -> None:
        make_repo(self.root)
        out = self.root / "lab" / "drafting" / "out"
        out.mkdir(parents=True)
        draft = {"notes": [{"function": "fixture_fn"}, {"function": "invented_fn", "trap": "`fixture_fn(1)`"}]}
        (out / "g.json").write_text(json.dumps(draft), encoding="utf-8")
        errors = check_repo.check_names(self.root)
        self.assertEqual(len(errors), 1)
        self.assertIn("'invented_fn'", errors[0])

    def test_names_without_catalogue_fail(self) -> None:
        make_repo(self.root, catalogue=False)
        self.write_skill("Use `fixture_fn(x)`.")
        self.assertEqual(len(check_repo.check_names(self.root)), 1)


if __name__ == "__main__":
    unittest.main()
