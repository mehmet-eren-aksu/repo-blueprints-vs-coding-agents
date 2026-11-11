#!/usr/bin/env python3
"""Score sqlfluff list_wrapping runs against the hidden PR #8580 tests.

Usage:
    python3 score.py run LABEL REPO_DIR   # copy repo, plant hidden tests, run pytest
    python3 score.py report [A:B ...]     # compare runs; pairs like a1:b1 a2:b2

Every run (base, oracle, arm-a ...) uses the same hidden test files and the
same pytest selection, so outcomes are directly comparable.

  acceptance  = tests the oracle passes and the base does not
  regression  = tests both the base and the oracle pass
  guard       = regression tests whose id mentions list_wrapping
  excluded    = tests the oracle does not pass (environment or flaky)

Only the standard library is used here. pytest runs in the scoring venv.
"""

import json
import os
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(os.environ.get("SQ_SECRET", Path.home() / "Desktop/contracts/sqlfluff"))
HIDDEN = HERE / "hidden"
WORK = HERE / "work"
RESULTS = HERE / "results"
VENV = HERE / "score-venv"

SELECTION = [
    "test/rules",
    "test/utils/reflow",
    "test/core/config",
    "test/core/rules",
    "test/api",
]
IGNORE = shutil.ignore_patterns(
    ".git", ".venv", "*.egg-info", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "node_modules", "blueprint",
)


def find_uv() -> str:
    uv = shutil.which("uv") or str(Path.home() / ".local/bin/uv")
    if not Path(uv).exists():
        sys.exit("uv not found. Run setup.sh first.")
    return uv


def parse_junit(path: Path) -> dict:
    out = {}
    for case in ET.parse(path).getroot().iter("testcase"):
        key = f"{case.get('classname')}::{case.get('name')}"
        status = "pass"
        for child in case:
            if child.tag in ("failure", "error"):
                status = "fail"
                break
            if child.tag == "skipped":
                status = "skip"
        # xdist can report setup and call errors twice; fail wins.
        if out.get(key) != "fail":
            out[key] = status
    return out


def cmd_run(label: str, repo: str) -> None:
    repo_path = Path(repo).expanduser().resolve()
    if not (repo_path / "src/sqlfluff").is_dir():
        sys.exit(f"{repo_path} does not look like a sqlfluff repo.")
    dest = WORK / label
    if dest.exists():
        shutil.rmtree(dest)
    WORK.mkdir(parents=True, exist_ok=True)
    print(f"[{label}] copying: {repo_path}")
    shutil.copytree(repo_path, dest, ignore=IGNORE)

    planted = 0
    for f in HIDDEN.rglob("*"):
        if f.is_file():
            target = dest / f.relative_to(HIDDEN)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, target)
            planted += 1
    print(f"[{label}] planted {planted} hidden test files")

    py = VENV / "bin/python"
    subprocess.run(
        [find_uv(), "pip", "install", "-q", "--python", str(py),
         "--no-deps", "-e", str(dest)],
        check=True,
    )

    RESULTS.mkdir(parents=True, exist_ok=True)
    xml = RESULTS / f"{label}.xml"
    if xml.exists():
        xml.unlink()
    print(f"[{label}] running pytest (this can take a few minutes)...")
    t0 = time.time()
    proc = subprocess.run(
        [str(py), "-m", "pytest", *SELECTION, "-n", "auto",
         "-p", "no:cacheprovider", "-q", "--no-header", "-rN",
         f"--junitxml={xml}"],
        cwd=dest, capture_output=True, text=True,
    )
    secs = round(time.time() - t0)
    (RESULTS / f"{label}.log").write_text(proc.stdout + proc.stderr)
    if not xml.exists():
        print(proc.stdout[-3000:], proc.stderr[-3000:])
        sys.exit(f"[{label}] no junit file was written, log: {RESULTS / (label + '.log')}")
    outcomes = parse_junit(xml)
    data = {"label": label, "repo": str(repo_path), "seconds": secs,
            "exit": proc.returncode, "outcomes": outcomes}
    (RESULTS / f"{label}.json").write_text(json.dumps(data, indent=1))
    counts = {s: sum(1 for v in outcomes.values() if v == s)
              for s in ("pass", "fail", "skip")}
    print(f"[{label}] done: {counts} ({secs} s)")
    print(f"[{label}] last line: {proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else '-'}")


def load(label: str) -> dict:
    p = RESULTS / f"{label}.json"
    if not p.exists():
        sys.exit(f"No result for {label}. First run: python3 score.py run {label} <folder>")
    return json.loads(p.read_text())["outcomes"]


def short(key: str) -> str:
    return key.split("::", 1)[1] if "::" in key else key


def cmd_report(pairs: list[str]) -> None:
    base, oracle = load("base"), load("oracle")
    acceptance = sorted(k for k, v in oracle.items()
                        if v == "pass" and base.get(k) != "pass")
    regression = sorted(k for k, v in oracle.items()
                        if v == "pass" and base.get(k) == "pass")
    guard = [k for k in regression if "list_wrapping" in k]
    excluded = sorted(k for k, v in oracle.items() if v != "pass")
    print(f"Acceptance tests: {len(acceptance)}   Regression: {len(regression)} "
          f"(guard: {len(guard)})   Excluded: {len(excluded)}")
    if len(acceptance) == 0:
        print("WARNING: the acceptance set is empty. Check the base and oracle results.")

    labels = sorted(p.stem for p in RESULTS.glob("*.json")
                    if p.stem not in ("base", "oracle"))
    summary = {}
    for label in labels:
        res = load(label)
        acc_fail = [k for k in acceptance if res.get(k) != "pass"]
        reg_broken = [k for k in regression if res.get(k) != "pass"]
        summary[label] = {
            "acc_fail": set(acc_fail),
            "reg_broken": set(reg_broken),
        }
        print(f"\n== {label} ==")
        print(f"  acceptance: {len(acceptance) - len(acc_fail)}/{len(acceptance)}")
        for k in acc_fail:
            print(f"    FAILED  {short(k)}")
        print(f"  regressions broken: {len(reg_broken)} "
              f"(guard: {sum(1 for k in reg_broken if k in guard)})")
        for k in reg_broken[:30]:
            print(f"    BROKE  {short(k)}")
        if len(reg_broken) > 30:
            print(f"    ... and {len(reg_broken) - 30} more")

    for pair in pairs:
        a, b = pair.split(":")
        if a not in summary or b not in summary:
            print(f"\n{pair}: missing results")
            continue
        ra, rb = summary[a]["reg_broken"], summary[b]["reg_broken"]
        # A's failures: failed acceptance tests plus broken regression tests.
        fa = summary[a]["acc_fail"] | ra
        fb = summary[b]["acc_fail"] | rb
        print(f"\n== Pair {a} / {b} ==")
        if not fa:
            print(f"  {a} failed no tests: the task is not discriminating.")
            verdict = None
        else:
            rescued = len(fa - fb)
            ratio = rescued / len(fa)
            print(f"  {b} passed {rescued} of the {len(fa)} tests {a} failed "
                  f"({ratio * 100:.0f}%, threshold 40%)")
            verdict = ratio >= 0.4
        extra = len(rb - ra)
        print(f"  regression tests {b} broke beyond {a}: {extra} (threshold 2)")
        reg_ok = extra <= 2
        if verdict is None:
            print("  Result: not discriminating")
        else:
            print(f"  Result: {'RULE MET' if verdict and reg_ok else 'rule not met'}")


def main() -> None:
    if len(sys.argv) >= 4 and sys.argv[1] == "run":
        cmd_run(sys.argv[2], sys.argv[3])
    elif len(sys.argv) >= 2 and sys.argv[1] == "report":
        cmd_report(sys.argv[2:])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
