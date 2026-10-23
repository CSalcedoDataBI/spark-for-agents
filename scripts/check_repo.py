"""Repository checks that run in CI (the required `Validate` check).

- Every skills/*/SKILL.md opens with frontmatter that has `name` (matching its folder) and
  `description`.
- Every workflow job sets `timeout-minutes` and runs on `ubuntu-latest`, and every workflow
  declares `concurrency` (Actions cost rules R2, R3, R5).
- No function name outside the exported catalogue: in what an agent reads (skills/**/*.md and
  the drafts in lab/drafting/out/), every inline code span written as a call, `name(...)` or
  `F.name(...)`, and every draft's `function` field must name something in exports/.

Standard library only, so CI needs no install step. Exit code 1 lists every failure.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# An inline code span that is a call: `name(...)`, `F.name(...)`, `df.name(...)`, `col.name(...)`.
CALL_SPAN = re.compile(r"`(?:[A-Za-z_][A-Za-z0-9_]*\.)?([A-Za-z_][A-Za-z0-9_]*)\([^`]*\)`")


def check_skills() -> list[str]:
    errors = []
    for skill in sorted((ROOT / "skills").glob("*/SKILL.md")):
        text = skill.read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        rel = skill.relative_to(ROOT).as_posix()
        if not match:
            errors.append(f"{rel}: missing frontmatter")
            continue
        fields = dict(
            line.split(":", 1) for line in match.group(1).splitlines() if ":" in line and not line.startswith(" ")
        )
        name = fields.get("name", "").strip()
        if name != skill.parent.name:
            errors.append(f"{rel}: name '{name}' does not match folder '{skill.parent.name}'")
        if not fields.get("description", "").strip():
            errors.append(f"{rel}: empty description")
    return errors


def check_workflows() -> list[str]:
    errors = []
    for wf in sorted((ROOT / ".github" / "workflows").glob("*.y*ml")):
        text = wf.read_text(encoding="utf-8")
        rel = wf.relative_to(ROOT).as_posix()
        if not re.search(r"^concurrency:", text, re.M):
            errors.append(f"{rel}: no top-level concurrency (R2)")
        jobs = len(re.findall(r"^\s+runs-on:", text, re.M))
        timeouts = len(re.findall(r"^\s+timeout-minutes:", text, re.M))
        if timeouts < jobs:
            errors.append(f"{rel}: {jobs} jobs but {timeouts} timeout-minutes (R3)")
        for runner in re.findall(r"^\s+runs-on:\s*(.+)$", text, re.M):
            if runner.strip() != "ubuntu-latest":
                errors.append(f"{rel}: runs-on {runner.strip()} (R5, and no self-hosted on a public repo)")
    return errors


def load_catalog(root: Path = ROOT) -> tuple[set[str], set[str]]:
    """Names from every export: SQL functions (lower case, SQL is case-insensitive) and PySpark."""
    sql: set[str] = set()
    api: set[str] = set()
    for path in (root / "exports").glob("spark-*/sql-functions.json"):
        sql |= {f["name"].lower() for f in json.loads(path.read_text(encoding="utf-8"))["functions"]}
    for path in (root / "exports").glob("spark-*/pyspark-api.json"):
        for members in json.loads(path.read_text(encoding="utf-8"))["modules"].values():
            api |= {m["name"] for m in members}
    return sql, api


def known(name: str, sql: set[str], api: set[str]) -> bool:
    return name in api or name.lower() in sql


def check_names(root: Path = ROOT) -> list[str]:
    sql, api = load_catalog(root)
    errors = []
    texts: list[tuple[str, str]] = []
    for md in sorted((root / "skills").glob("**/*.md")):
        texts.append((md.relative_to(root).as_posix(), md.read_text(encoding="utf-8")))
    for draft in sorted((root / "lab" / "drafting" / "out").glob("**/*.json")):
        rel = draft.relative_to(root).as_posix()
        data = json.loads(draft.read_text(encoding="utf-8"))
        for note in data.get("notes", []):
            name = note.get("function", "")
            if not known(name, sql, api):
                errors.append(f"{rel}: function '{name}' is not in the exported catalogue")
        texts.append((rel, json.dumps(data, ensure_ascii=False)))
    if texts and not (sql or api):
        return [f"{texts[0][0]}: names to check but no catalogue under exports/"]
    for rel, text in texts:
        for name in sorted(set(CALL_SPAN.findall(text))):
            if not known(name, sql, api):
                errors.append(f"{rel}: `{name}(...)` is not in the exported catalogue")
    return errors


def main() -> int:
    errors = check_skills() + check_workflows() + check_names()
    for error in errors:
        print(f"FAIL {error}")
    if not errors:
        print("OK repo checks")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
