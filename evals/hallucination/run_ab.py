#!/usr/bin/env python3
"""Measure the one thing this library exists for: does the reference stop invented names?

Same design as powerquery-m-for-agents and dax-for-agents (their evals/hallucination/run_ab.py),
ported to Spark. Every question is asked twice, of the same model:

    arm A   the question alone
    arm B   the question, plus the catalogue rows of its category

Arm B is deliberately NOT the card that holds the answer. Handing over the answer would measure
obedience, not invention. The rows are names and one-line summaries -- what an agent reads before
opening anything -- so arm B knows what exists and still has to choose.

## The metric is mechanical

No model judges another. The surface a Spark agent invents on is FUNCTION NAMES: the PySpark SQL
functions (`F.<name>`) and the SQL functions used inside `spark.sql(...)`/`expr(...)` strings. In
an answer's runnable ```python code, every `F.<name>(...)` / `functions.<name>(...)` call is looked
up against the exported PySpark function members and SQL functions (the same catalogue CI's
scripts/check_repo.py enforces), and every `name(...)` inside a SQL string passed to sql / expr /
selectExpr is looked up against the SQL functions. A name neither catalogue has is an invention.

Only fenced code is scanned, not inline prose: a model naming a wrong function in a sentence to
contrast it is not inventing it. DataFrame/Column *methods* are not scored -- they are rarely the
hallucination and scaffolding (`spark.createDataFrame`, `.collect`) would add noise; the function
surface is what this library documents and what agents get wrong.

    python evals/hallucination/run_ab.py --limit 3          # a few questions
    python evals/hallucination/run_ab.py --out run.json     # the whole bank
    python evals/hallucination/run_ab.py --replay run.json  # re-count, no API calls
    python evals/hallucination/run_ab.py --out run.json --resume   # finish an interrupted run

The provider is read from the model's name, and each has its own key variable: ANTHROPIC_API_KEY
for `claude-*`, DEEPSEEK_API_KEY for `deepseek-*`. A key is read from the environment and nowhere
else: never passed on the command line, never printed, never written into the output file.
"""
import argparse
import ast
import json
import os
import re
import sys

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml not installed (pip install pyyaml)")
    sys.exit(2)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import check_repo as cr  # noqa: E402

QUESTIONS = os.path.join(HERE, "questions.yaml")
FENCE = re.compile(r"```(?:python|py)\n(.*?)```", re.S)
# SQL syntax that reads as a function call but is grammar, not a catalogue function.
SQL_SYNTAX = frozenset({"cast", "extract", "trim", "substring", "position", "overlay",
                        "convert", "values", "table", "lateral", "nullif", "coalesce"})
# PySpark functions are reached through these call strings as SQL.
SQL_ENTRY = frozenset({"sql", "expr", "selectExpr", "filter", "where"})


def _read_json(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return json.load(f)


def _catalog():
    """(F-members, sql-names, merged-api, rows-by-category). Cached on the function object."""
    if getattr(_catalog, "_c", None) is None:
        modules = _read_json("exports", "spark-3.5.9", "pyspark-api.json")["modules"]
        f_members = {m["name"] for m in modules["pyspark.sql.functions"]}
        sql, api = cr.load_catalog()

        def first_line(doc):
            for line in (doc or "").splitlines():
                if line.strip():
                    return line.strip()
            return ""

        rows = {}
        rows["functions"] = [f"- {m['name']}: {first_line(m.get('doc'))}".rstrip(": ")
                             for m in modules["pyspark.sql.functions"]]
        for mod, key in (("pyspark.sql.dataframe.DataFrame", "DataFrame"),
                         ("pyspark.sql.column.Column", "Column")):
            rows[key] = [f"- {m['name']}: {first_line(m.get('doc'))}".rstrip(": ")
                         for m in modules[mod]]
        sqlfns = _read_json("exports", "spark-3.5.9", "sql-functions.json")["functions"]
        rows["sql-functions"] = [f"- {fn['name']}: {(fn.get('info') or {}).get('usage', '')}"
                                 .replace("\n", " ").strip().rstrip(": ") for fn in sqlfns]
        _catalog._c = (f_members, sql, api, rows)
    return _catalog._c


def catalog_rows():
    return _catalog()[3]


# --- the metric: invented function names in runnable code ------------------------------------

_SQL_CALL = re.compile(r"\b([A-Za-z_]\w*)\s*\(")


def _sql_invented(sql_text, sql_names):
    bad = []
    for m in _SQL_CALL.finditer(sql_text):
        name = m.group(1)
        low = name.lower()
        if low in sql_names or low in SQL_SYNTAX:
            continue
        bad.append(f"`{name}(...)` (in SQL) is not a Spark SQL function")
    return bad


def invented(text):
    """Invented Spark function names in an answer's runnable ```python code: `F.<name>` /
    `functions.<name>` calls not in the PySpark function members or SQL functions, and `name(...)`
    inside a sql/expr/selectExpr string not in the SQL functions. Returns a de-duplicated list."""
    f_members, sql, api, _ = _catalog()
    valid_func = f_members | sql
    seen, bad = set(), []

    def add(msg):
        if msg not in seen:
            seen.add(msg)
            bad.append(msg)

    for block in FENCE.findall(text or ""):
        try:
            tree = ast.parse(block)
        except SyntaxError:
            continue  # unparseable code checks nothing, like an empty answer
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            # F.<name>(...) / functions.<name>(...)
            if (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)
                    and func.value.id in ("F", "functions")):
                if func.attr not in valid_func:
                    add(f"`F.{func.attr}` is not a PySpark SQL function")
            # SQL strings passed to sql / expr / selectExpr / filter / where
            callee = func.attr if isinstance(func, ast.Attribute) else (
                func.id if isinstance(func, ast.Name) else None)
            if callee in SQL_ENTRY:
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        for msg in _sql_invented(arg.value, sql):
                            add(msg)
    return bad


# --- asking a model (provider by name; standard library only) --------------------------------

MAX_TOKENS = 4000

SYSTEM = ("You are a PySpark developer answering a colleague, using Spark 3.5. Be brief: name the "
          "Spark SQL functions involved (as `F.<name>` or in a spark.sql string) and show a short "
          "snippet. Do not hedge with lists of alternatives you are unsure about.")


def _user(question, reference):
    if not reference:
        return question
    return (f"{question}\n\n---\nSpark names available in this category, from the reference:"
            f"\n\n{reference}")


def _anthropic_request(model, question, reference, system, max_tokens):
    return {"model": model, "max_tokens": max_tokens, "system": system,
            "messages": [{"role": "user", "content": _user(question, reference)}]}


def _anthropic_read(out):
    usage = dict(out.get("usage", {}))
    usage["stop_reason"] = out.get("stop_reason")
    text = "".join(b.get("text", "") for b in out.get("content", []))
    return text, usage


def _openai_request(model, question, reference, system, max_tokens):
    return {"model": model, "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": _user(question, reference)}]}


def _openai_read(out):
    choice = (out.get("choices") or [{}])[0]
    raw = out.get("usage", {}) or {}
    usage = {"input_tokens": raw.get("prompt_tokens", 0),
             "output_tokens": raw.get("completion_tokens", 0),
             "stop_reason": choice.get("finish_reason")}
    return (choice.get("message") or {}).get("content") or "", usage


PROVIDERS = {
    "anthropic": {
        "prefixes": ("claude-",),
        "url": "https://api.anthropic.com/v1/messages",
        "key_env": "ANTHROPIC_API_KEY",
        "headers": lambda key: {"x-api-key": key, "anthropic-version": "2023-06-01",
                                "content-type": "application/json"},
        "request": _anthropic_request,
        "read": _anthropic_read,
    },
    "deepseek": {
        "prefixes": ("deepseek-",),
        "url": "https://api.deepseek.com/chat/completions",
        "key_env": "DEEPSEEK_API_KEY",
        "headers": lambda key: {"Authorization": f"Bearer {key}",
                                "content-type": "application/json"},
        "request": _openai_request,
        "read": _openai_read,
    },
}


def provider_for(model):
    for name, spec in PROVIDERS.items():
        if model.startswith(spec["prefixes"]):
            return name, spec
    raise SystemExit(f"ERROR: no provider is configured for '{model}'. Known prefixes: "
                     + ", ".join(p for s in PROVIDERS.values() for p in s["prefixes"]))


def ask(model, key, question, reference=None, timeout=180):
    import urllib.request
    _, spec = provider_for(model)
    body = json.dumps(spec["request"](model, question, reference, SYSTEM, MAX_TOKENS)).encode()
    req = urllib.request.Request(spec["url"], data=body, headers=spec["headers"](key))
    with urllib.request.urlopen(req, timeout=timeout) as r:
        out = json.load(r)
    return spec["read"](out)


def describe(exc):
    import urllib.error
    if isinstance(exc, urllib.error.HTTPError):
        try:
            body = json.loads(exc.read().decode("utf-8", "replace"))
            message = (body.get("error") or {}).get("message") or json.dumps(body)[:200]
        except Exception:  # noqa: BLE001
            message = exc.reason
        return f"HTTP {exc.code}: {message}"
    return f"{type(exc).__name__}: {exc}"


# --- counting and reporting ------------------------------------------------------------------

def answered(rec):
    return all((rec[arm].get("text") or "").strip()
               and rec[arm].get("stop_reason") != "refusal" for arm in ("A", "B"))


def summarise(records):
    by_regime = {}
    for rec in records:
        slot = by_regime.setdefault(rec["regime"], {"n": 0, "A": 0, "B": 0,
                                                    "A_q": 0, "B_q": 0, "dropped": 0})
        if not answered(rec):
            slot["dropped"] += 1
            continue
        slot["n"] += 1
        for arm in ("A", "B"):
            bad = invented(rec[arm]["text"])
            slot[arm] += len(bad)
            slot[arm + "_q"] += 1 if bad else 0
    return by_regime


def refusals(records):
    return [f"{r['id']} {arm}" for r in records for arm in ("A", "B")
            if r[arm].get("stop_reason") == "refusal"]


def report(records):
    print()
    print(f"{'question':<28} {'regime':<6} {'invented A':>11} {'invented B':>11}")
    print("-" * 60)
    for rec in records:
        a = invented(rec["A"]["text"])
        b = invented(rec["B"]["text"])
        print(f"{rec['id']:<28} {rec['regime']:<6} {len(a):>11} {len(b):>11}")
        if a:
            print(f"{'':<28} A invented: {', '.join(a)}")
        if b:
            print(f"{'':<28} B invented: {', '.join(b)}")
    print()
    by_regime = summarise(records)
    print(f"{'regime':<10} {'questions':>9} {'A invented':>11} {'B invented':>11} "
          f"{'A q. with':>10} {'B q. with':>10} {'dropped':>8}")
    print("-" * 77)
    for regime in sorted(by_regime):
        s = by_regime[regime]
        print(f"{regime:<10} {s['n']:>9} {s['A']:>11} {s['B']:>11} "
              f"{s['A_q']:>10} {s['B_q']:>10} {s['dropped']:>8}")
    total_a = sum(s["A"] for s in by_regime.values())
    total_b = sum(s["B"] for s in by_regime.values())
    compared = sum(s["n"] for s in by_regime.values())
    dropped = sum(s["dropped"] for s in by_regime.values())
    print("-" * 77)
    print(f"{'TOTAL':<10} {compared:>9} {total_a:>11} {total_b:>11} {'':>10} {'':>10} {dropped:>8}")

    refused = refusals(records)
    if refused:
        print(f"\nREFUSED by the model ({len(refused)} answer(s)): {', '.join(refused)}")
    if dropped:
        print(f"\n{dropped} question(s) dropped: a question is compared only when both arms "
              f"answered.")
    return total_a, total_b


# --- run files -------------------------------------------------------------------------------

def save(path, model, provider, records):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"model": model, "provider": provider, "records": records}, f,
                  ensure_ascii=False, indent=2)


def already_answered(path):
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            saved = json.load(f)
    except (OSError, ValueError):
        return {}

    def finished(arm):
        return arm is not None and ((arm.get("text") or "").strip() or arm.get("stop_reason"))
    return {r["id"]: r for r in saved.get("records", [])
            if finished(r.get("A")) and finished(r.get("B"))}


def other_model(path, model):
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            saved = json.load(f).get("model")
    except (OSError, ValueError):
        return None
    return saved if saved and saved != model else None


def load_questions(path=QUESTIONS):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)["questions"]


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="ask only the first N questions")
    ap.add_argument("--regime", help="core | deep")
    ap.add_argument("--model", default=os.environ.get("EVAL_MODEL", "claude-haiku-5-5"))
    ap.add_argument("--out", help="write every answer to this JSON file")
    ap.add_argument("--replay", help="re-count a saved run, making no API calls")
    ap.add_argument("--resume", action="store_true",
                    help="keep the answers already in --out and ask only what is missing")
    args = ap.parse_args(argv)

    if args.replay:
        with open(args.replay, encoding="utf-8") as f:
            saved = json.load(f)
        print(f"replaying {len(saved['records'])} question(s) from {args.replay} "
              f"(model {saved.get('model', '?')}) - no API calls.")
        report(saved["records"])
        return 0

    if args.resume and (args.limit or args.regime) and args.out and os.path.exists(args.out):
        print("ERROR: --resume rewrites the whole run file; it cannot be combined with --limit "
              "or --regime. Resume the full bank, or write to another --out.")
        return 2
    other = other_model(args.out, args.model) if args.resume else None
    if other:
        print(f"ERROR: {args.out} holds answers from {other}, not {args.model}. Resume it with "
              f"--model {other}, or write to another --out.")
        return 2

    rows = catalog_rows()
    questions = load_questions()
    if args.regime:
        questions = [q for q in questions if q["regime"] == args.regime]
    if args.limit:
        questions = questions[:args.limit]
    if not questions:
        print("no questions selected.")
        return 2

    provider, spec = provider_for(args.model)
    key = os.environ.get(spec["key_env"])
    if not key:
        print(f"ERROR: {spec['key_env']} is not set in the environment "
              f"({args.model} is served by {provider}).")
        return 2

    print(f"model {args.model} ({provider}) - {len(questions)} question(s) - 2 arms each "
          f"= {len(questions) * 2} calls")
    done = already_answered(args.out) if args.resume else {}
    if done:
        print(f"  resuming: {len(done)} question(s) already answered in {args.out}")
    records = [done[q["id"]] for q in questions if q["id"] in done]
    consecutive = 0
    tokens_in = tokens_out = 0
    for q in questions:
        if q["id"] in done:
            continue
        if q["category"] not in rows:
            raise SystemExit(f"{q['id']}: category '{q['category']}' is not a catalogue group")
        reference = "\n".join(rows[q["category"]])
        rec = {"id": q["id"], "regime": q["regime"], "category": q["category"],
               "question": q["question"]}
        for arm, ref in (("A", None), ("B", reference)):
            try:
                text, usage = ask(args.model, key, q["question"], ref)
                consecutive = 0
            except Exception as exc:  # noqa: BLE001
                consecutive += 1
                print(f"  {q['id']} arm {arm}: FAILED - {describe(exc)}")
                text, usage = "", {}
            rec[arm] = {"text": text, "stop_reason": usage.get("stop_reason")}
            tokens_in += usage.get("input_tokens", 0)
            tokens_out += usage.get("output_tokens", 0)
        if consecutive >= 4:
            print(f"\n{consecutive} calls failed in a row. Stopping: a run of empty answers is "
                  f"not a measurement.")
            if args.out and records:
                save(args.out, args.model, provider, records)
            return 2
        records.append(rec)
        if args.out:
            save(args.out, args.model, provider, records)
        print(f"  {q['id']:<28} A={len(invented(rec['A']['text']))} "
              f"B={len(invented(rec['B']['text']))}", flush=True)

    report(records)
    print(f"\ntokens: {tokens_in} in, {tokens_out} out")
    if args.out:
        save(args.out, args.model, provider, records)
        print(f"answers written to {args.out} - re-count with --replay")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
