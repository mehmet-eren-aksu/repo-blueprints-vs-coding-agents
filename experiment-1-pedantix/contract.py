#!/usr/bin/env python3
"""Black-box contract runner for CLI tools (stdlib only).

A contract suite is a folder of cases. Each case is a JSON file:

  {
    "id": "sort-attrs-basic",
    "feature": "sort.attrs",
    "desc": "Bindings of an attrset are sorted by name",
    "args": ["--config-toml", "formatter = \"off\""],
    "stdin": "{ b = 1; a = 2; }\n",          # optional
    "files": {"one.nix": "..."},             # optional, written before the run
    "dirs": [".git"],                        # optional, created before the run
    "env": {"XDG_CONFIG_HOME": "{tmp}/xdg"}, # optional, merged over the isolated env
    "cwd": "sub",                            # optional, relative to the temp dir
    "compare": ["exit", "stdout", "files"],  # what the contract binds (default: all three)
    "watch_files": ["one.nix"],              # files whose content after the run is compared
    "stderr_contains": ["would reformat"],   # hand-written, optional
    "idempotent": true                       # rerun stdout through the tool, must not change
  }

"{tmp}" in args, env and file contents is replaced with the case's temp dir.

Modes:
  record  run the ORIGINAL tool twice per case and store what it did in
          expected/<id>.json; cases whose two runs differ are marked flaky
          and left out of the contract.
  check   run any implementation against the recorded expectations and
          print a score.

Usage:
  python3 contract.py record --bin /path/to/original --suite suites/pedantix
  python3 contract.py check  --bin "/path/to/new-impl" --suite suites/pedantix
  python3 contract.py calibrate --suite suites/pedantix   # writes weak.json
"""

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TIMEOUT = 30


def subst(value, tmp):
    if isinstance(value, str):
        return value.replace("{tmp}", tmp)
    if isinstance(value, list):
        return [subst(v, tmp) for v in value]
    if isinstance(value, dict):
        return {k: subst(v, tmp) for k, v in value.items()}
    return value


def run_case(bin_cmd, case):
    tmp = tempfile.mkdtemp(prefix="contract-")
    try:
        root = Path(tmp)
        for d in case.get("dirs", []):
            (root / d).mkdir(parents=True, exist_ok=True)
        for rel, content in case.get("files", {}).items():
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(subst(content, tmp))
        # Isolated environment: no user config leaks into the run.
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(root / "home"),
            "XDG_CONFIG_HOME": str(root / "xdg-empty"),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
        }
        env.update(subst(case.get("env", {}), tmp))
        cwd = root / case.get("cwd", ".")
        cwd.mkdir(parents=True, exist_ok=True)
        argv = bin_cmd + subst(case.get("args", []), tmp)
        stdin = case.get("stdin")

        def invoke(stdin_text):
            try:
                p = subprocess.run(
                    argv,
                    input=(stdin_text if stdin_text is not None else ""),
                    capture_output=True,
                    text=True,
                    cwd=cwd,
                    env=env,
                    timeout=TIMEOUT,
                )
                return p.returncode, p.stdout, p.stderr
            except subprocess.TimeoutExpired:
                return "timeout", "", "timeout"
            except FileNotFoundError as e:
                return "not-found", "", str(e)

        code, out, err = invoke(stdin)
        files_after = {}
        for rel in case.get("watch_files", []):
            p = root / rel
            files_after[rel] = p.read_text() if p.exists() else None
        idem = None
        if case.get("idempotent") and code == 0:
            code2, out2, _ = invoke(out)
            idem = code2 == 0 and out2 == out
        # Paths in stderr depend on the temp dir; normalise them.
        err = err.replace(tmp, "{tmp}")
        return {"exit": code, "stdout": out, "stderr": err, "files": files_after, "idempotent": idem}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


class _RawJson:
    """Minimal JSON parser that keeps what a contract binds and drops what it does not.

    Kept: object key order (keys compared after decoding), array order, and the
    raw source text of every scalar (so 1.0 != 1 and "\\u00e9" != "é").
    Dropped: whitespace and layout.
    """

    WS = " \t\r\n"

    def __init__(self, text):
        self.s, self.i = text, 0

    def parse(self):
        v = self.value()
        self.skip()
        if self.i != len(self.s):
            raise ValueError("trailing data")
        return v

    def skip(self):
        while self.i < len(self.s) and self.s[self.i] in self.WS:
            self.i += 1

    def value(self):
        self.skip()
        c = self.s[self.i:self.i + 1]
        if c == "{":
            return self.obj()
        if c == "[":
            return self.arr()
        if c == '"':
            return ("s", self.string_raw())
        j = self.i
        while self.i < len(self.s) and self.s[self.i] not in self.WS + ",]}":
            self.i += 1
        tok = self.s[j:self.i]
        if not tok:
            raise ValueError("empty value")
        json.loads(tok)  # validates numbers / true / false / null
        return ("v", tok)

    def string_raw(self):
        j = self.i
        self.i += 1
        while True:
            if self.i >= len(self.s):
                raise ValueError("unterminated string")
            c = self.s[self.i]
            if c == "\\":
                self.i += 2
                continue
            self.i += 1
            if c == '"':
                return self.s[j:self.i]

    def obj(self):
        self.i += 1
        items = []
        self.skip()
        if self.s[self.i:self.i + 1] == "}":
            self.i += 1
            return ("o", items)
        while True:
            self.skip()
            key = json.loads(self.string_raw())
            self.skip()
            if self.s[self.i:self.i + 1] != ":":
                raise ValueError("expected ':'")
            self.i += 1
            items.append((key, self.value()))
            self.skip()
            c = self.s[self.i:self.i + 1]
            self.i += 1
            if c == "}":
                return ("o", items)
            if c != ",":
                raise ValueError("expected ',' or '}'")

    def arr(self):
        self.i += 1
        items = []
        self.skip()
        if self.s[self.i:self.i + 1] == "]":
            self.i += 1
            return ("a", items)
        while True:
            items.append(self.value())
            self.skip()
            c = self.s[self.i:self.i + 1]
            self.i += 1
            if c == "]":
                return ("a", items)
            if c != ",":
                raise ValueError("expected ',' or ']'")


def parse_json_raw(text):
    if text is None:
        return None
    try:
        return _RawJson(text).parse()
    except (ValueError, IndexError, json.JSONDecodeError):
        return None


def json_equal(got, want):
    w = parse_json_raw(want)
    return w is not None and parse_json_raw(got) == w


def resolve_bin(bin_str):
    """Split the --bin command and make relative paths absolute.

    Cases run inside a temp dir, so a relative path such as
    ./target/release/tool or contracts/dummy.py would not resolve there.
    """
    parts = shlex.split(bin_str)
    out = []
    for i, tok in enumerate(parts):
        looks_like_path = os.sep in tok or tok.startswith(".")
        if looks_like_path and os.path.exists(tok):
            tok = os.path.abspath(tok)
        elif i == 0 and not os.path.exists(tok):
            found = shutil.which(tok)
            if found is None:
                sys.exit(f"--bin: cannot find {tok!r}")
        out.append(tok)
    return out


def load_weak(suite):
    p = Path(suite) / "weak.json"
    return set(json.loads(p.read_text())) if p.exists() else set()


def load_cases(suite):
    cases = []
    for p in sorted((Path(suite) / "cases").glob("*.json")):
        case = json.loads(p.read_text())
        case.setdefault("id", p.stem)
        cases.append(case)
    return cases


def record(args):
    bin_cmd = resolve_bin(args.bin)
    exp_dir = Path(args.suite) / "expected"
    exp_dir.mkdir(exist_ok=True)
    kept = flaky = 0
    for case in load_cases(args.suite):
        a, b = run_case(bin_cmd, case), run_case(bin_cmd, case)
        stable = {k: a[k] for k in ("exit", "stdout", "files")} == {k: b[k] for k in ("exit", "stdout", "files")}
        problems = []
        if not stable:
            problems.append("flaky: two runs of the original differ")
        for s in case.get("stderr_contains", []):
            if s not in a["stderr"]:
                problems.append(f"stderr does not contain {s!r}")
        if case.get("idempotent") and a["idempotent"] is False:
            problems.append("original is not idempotent on this input")
        entry = {
            "id": case["id"],
            "valid": not problems,
            "problems": problems,
            "exit": a["exit"],
            "stdout": a["stdout"],
            "files": a["files"],
            "stderr_sample": a["stderr"][:400],
        }
        (exp_dir / f"{case['id']}.json").write_text(json.dumps(entry, indent=2, ensure_ascii=False) + "\n")
        if problems:
            flaky += 1
            print(f"DROP  {case['id']}: {'; '.join(problems)}")
        else:
            kept += 1
            print(f"KEEP  {case['id']}  exit={a['exit']}")
    print(f"\n{kept} cases enter the contract, {flaky} dropped.")


def check(args):
    bin_cmd = resolve_bin(args.bin)
    weak = load_weak(args.suite)
    exp_dir = Path(args.suite) / "expected"
    results = []
    for case in load_cases(args.suite):
        ep = exp_dir / f"{case['id']}.json"
        if not ep.exists():
            continue
        exp = json.loads(ep.read_text())
        if not exp["valid"]:
            continue
        got = run_case(bin_cmd, case)
        compare = case.get("compare", ["exit", "stdout", "files"])
        fails = []
        if "exit" in compare and got["exit"] != exp["exit"]:
            fails.append(f"exit {got['exit']} != {exp['exit']}")
        if "stdout" in compare and got["stdout"] != exp["stdout"]:
            fails.append("stdout differs")
        if "files" in compare and got["files"] != exp["files"]:
            fails.append("files differ")
        if "json:stdout" in compare and not json_equal(got["stdout"], exp["stdout"]):
            fails.append("json stdout differs")
        exact_files = set(case.get("exact_files", []))
        if "json:files" in compare:
            for rel, want in exp["files"].items():
                if rel in exact_files:
                    continue
                if not json_equal(got["files"].get(rel), want):
                    fails.append(f"json file {rel} differs")
        for rel in exact_files:
            if got["files"].get(rel) != exp["files"].get(rel):
                fails.append(f"file {rel} differs")
        for s in case.get("stderr_contains", []):
            if s not in got["stderr"]:
                fails.append(f"stderr missing {s!r}")
        if case.get("idempotent") and got["idempotent"] is False:
            fails.append("not idempotent")
        results.append((case["id"], case.get("feature", ""), fails))
        if args.verbose or fails:
            print(("PASS  " if not fails else "FAIL  ") + case["id"] + ("" if not fails else "  " + "; ".join(fails)))
    passed = sum(1 for _, _, f in results if not f)
    total = len(results)
    by_feature = {}
    for _, feat, f in results:
        top = feat.split(".")[0] or "other"
        p, t = by_feature.get(top, (0, 0))
        by_feature[top] = (p + (not f), t + 1)
    print("\nBy feature:")
    for feat, (p, t) in sorted(by_feature.items()):
        print(f"  {feat:12s} {p}/{t}")
    score = 100.0 * passed / total if total else 0.0
    strong = [(i, f) for i, _, f in results if i not in weak]
    s_passed = sum(1 for _, f in strong if not f)
    s_score = 100.0 * s_passed / len(strong) if strong else 0.0
    print(f"\nSCORE {passed}/{total} = {score:.1f}%")
    if weak:
        print(f"DISCRIMINATING SCORE {s_passed}/{len(strong)} = {s_score:.1f}%  "
              f"(leaves out {len(weak)} cases a do-nothing implementation passes)")
    if args.json:
        Path(args.json).write_text(json.dumps({"passed": passed, "total": total, "score": score,
                                               "discriminating_passed": s_passed,
                                               "discriminating_total": len(strong),
                                               "discriminating_score": s_score,
                                               "failed": [i for i, _, f in results if f],
                                               "passed_ids": [i for i, _, f in results if not f]},
                                              indent=2) + "\n")
    return 0 if passed == total else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)
    cal = sub.add_parser("calibrate", help="run the do-nothing dummy and write weak.json")
    cal.add_argument("--suite", required=True)
    for name in ("record", "check"):
        p = sub.add_parser(name)
        p.add_argument("--bin", required=True, help="command that runs the tool, e.g. ./target/release/pedantix")
        p.add_argument("--suite", required=True, help="suite folder containing cases/")
        if name == "check":
            p.add_argument("--verbose", action="store_true")
            p.add_argument("--json", help="write a score summary to this file")
    args = ap.parse_args()
    if args.mode == "calibrate":
        dummy = Path(__file__).resolve().with_name("dummy.py")
        weak_path = Path(args.suite) / "weak.json"
        if weak_path.exists():
            weak_path.unlink()
        out = Path(args.suite) / "dummy-score.json"
        ns = argparse.Namespace(bin=f"{shlex.quote(sys.executable)} {shlex.quote(str(dummy))}",
                                suite=args.suite, verbose=False, json=str(out))
        check(ns)
        weak_ids = json.loads(out.read_text())["passed_ids"]
        weak_path.write_text(json.dumps(sorted(weak_ids), indent=2) + "\n")
        print(f"\nwrote {weak_path} with {len(weak_ids)} weak cases")
        return 0
    if args.mode == "record":
        record(args)
        return 0
    return check(args)


if __name__ == "__main__":
    sys.exit(main())
