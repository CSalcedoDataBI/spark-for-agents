"""Tests for the pure parts of scripts/export_catalog.py (no pyspark needed)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import export_catalog  # noqa: E402

DOC = """Do something.

.. versionadded:: 1.3.0

.. versionchanged:: 3.4.0
    Supports Spark Connect.

Parameters
----------
key
    a literal value.

    .. deprecated:: 3.0.0
        Passing an object here is deprecated.
other
    .. versionadded:: 3.1.0
    .. versionadded:: 3.1.0

.. versionchanged:: 3.4.0
"""


class DocVersionsTest(unittest.TestCase):
    def test_member_and_parameter_directives_are_apart(self) -> None:
        member, parameter = export_catalog.doc_versions(DOC)
        self.assertEqual(member, {"versionadded": ["1.3.0"], "versionchanged": ["3.4.0"]})
        self.assertEqual(parameter, {"deprecated": ["3.0.0"], "versionadded": ["3.1.0"]})

    def test_empty_doc(self) -> None:
        self.assertEqual(export_catalog.doc_versions(""), ({}, {}))


if __name__ == "__main__":
    unittest.main()
