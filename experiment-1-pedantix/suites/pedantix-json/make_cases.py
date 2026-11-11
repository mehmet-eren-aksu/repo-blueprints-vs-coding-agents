#!/usr/bin/env python3
"""Generates the JSON acceptance suite for the pedantix adaptation experiment.

There is no original implementation to record from, so expectations are written
by hand. Each expected output is produced by `expect(...)`, a tiny reference
sorter that applies the rules stated in each case, and every case was reviewed.

Two groups (the `feature` prefix):
  g2.*  core consistency: does JSON support follow pedantix's existing (often
        undocumented) rules? Byte-order sorting, `sort = false` ignoring `first`,
        `*` / `**` override globs, later overrides winning, config discovery
        stopping at the git root, `--check` exit codes, invalid input -> 2.
        Each of these rules was confirmed on the original pedantix's Nix
        behaviour (suites/pedantix/expected).
  g3.*  the new feature itself: JSON objects sorted, arrays handled, values
        kept verbatim, config sections applied.

Comparison: JSON outputs are compared with `json:stdout` / `json:files`, which
ignore whitespace and layout but keep key order and the raw text of every
scalar. Exit codes and empty stdout are compared exactly.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
from contract import parse_json_raw  # noqa: E402

OFF = 'formatter = "off"'
CASES = []


# ------------------------------------------------------------ reference sorter
def render(node, ind=0):
    pad, pad2 = "  " * ind, "  " * (ind + 1)
    kind = node[0]
    if kind in ("s", "v"):
        return node[1]
    if kind == "a":
        if not node[1]:
            return "[]"
        return "[\n" + ",\n".join(pad2 + render(x, ind + 1) for x in node[1]) + "\n" + pad + "]"
    if not node[1]:
        return "{}"
    return "{\n" + ",\n".join(pad2 + json.dumps(k, ensure_ascii=False) + ": " + render(v, ind + 1)
                             for k, v in node[1]) + "\n" + pad + "}"


def order_keys(items, rule):
    if not rule.get("sort", True):
        return list(items)  # sort = false keeps the order and ignores first/last
    first, last = rule.get("first", []), rule.get("last", [])
    head = [it for name in first for it in items if it[0] == name]
    tail = [it for name in last for it in items if it[0] == name and name not in first]
    pinned = {id(x) for x in head + tail}
    middle = sorted((it for it in items if id(it) not in pinned), key=lambda kv: kv[0])
    return head + middle + tail


def apply(node, rules, path=()):
    kind = node[0]
    if kind == "o":
        items = [(k, apply(v, rules, path + (k,))) for k, v in node[1]]
        return ("o", order_keys(items, rules(path, "attrs")))
    if kind == "a":
        items = [apply(x, rules, path) for x in node[1]]
        if rules(path, "lists").get("sort", False):
            items = sorted(items, key=lambda x: render(x))
        return ("a", items)
    return node


def expect(text, rules=None):
    rules = rules or (lambda path, kind: {})
    tree = parse_json_raw(text)
    assert tree is not None, text
    return render(apply(tree, rules)) + "\n"


def case(id, feature, desc, expected, **kw):
    c = {"id": id, "feature": feature, "desc": desc}
    c.update(kw)
    CASES.append((c, expected))


def cfg(*lines):
    return ["--config-toml", "\n".join([OFF, *lines])]


def stdin_json(name="data.json"):
    return ["--stdin-filepath", "{tmp}/" + name]


JS = ["exit", "json:stdout"]          # stdin mode, JSON on stdout
JF = ["exit", "json:files", "stdout"]  # file mode: JSON written in place, nothing on stdout


def out(stdout="", exit=0, files=None):
    return {"exit": exit, "stdout": stdout, "files": files or {}}


# ====================================================== g3: the feature itself
src = '{"b": 1, "a": 2}\n'
case("g3-stdin-basic", "g3.basic", "--stdin-filepath *.json: keys of an object are sorted",
     out(expect(src)), args=cfg() + stdin_json(), stdin=src, compare=JS)

src = '{\n  "z": {"y": 1, "x": {"q": 1, "p": 2}},\n  "a": 1\n}\n'
case("g3-nested", "g3.basic", "Objects are sorted at every depth",
     out(expect(src)), args=cfg() + stdin_json(), stdin=src, compare=JS)

src = '[{"b": 1, "a": 2}, {"d": 1, "c": 2}]\n'
case("g3-objects-in-array", "g3.arrays", "Objects inside an array are sorted, the array order stays",
     out(expect(src)), args=cfg() + stdin_json(), stdin=src, compare=JS)

src = '{"xs": ["b", "a", "c"], "n": [3, 1, 2]}\n'
case("g3-arrays-unsorted-by-default", "g3.arrays", "Arrays keep their order by default ([lists] sort is off)",
     out(expect(src)), args=cfg() + stdin_json(), stdin=src, compare=JS)

src = '{"xs": ["b", "a", "c"]}\n'
case("g3-lists-sort", "g3.arrays", "[lists] sort = true sorts arrays of strings",
     out(expect(src, lambda p, k: {"sort": True} if k == "lists" else {})),
     args=cfg("[lists]", "sort = true") + stdin_json(), stdin=src, compare=JS)

src = '[3, 1, 2]\n'
case("g3-top-level-array", "g3.arrays", "A top-level array of scalars is left as is",
     out(expect(src)), args=cfg() + stdin_json(), stdin=src, compare=JS)

src = ('{"z": 1.0, "y": 1e10, "x": 12345678901234567890, "w": -0, '
       '"v": "caf\\u00e9\\n", "u": true, "t": null, "s": "tab\\there"}\n')
case("g3-values-verbatim", "g3.values", "Numbers and strings are kept exactly as written",
     out(expect(src)), args=cfg() + stdin_json(), stdin=src, compare=JS)

src = '{"b": {}, "a": []}\n'
case("g3-empty-containers", "g3.basic", "Empty objects and arrays",
     out(expect(src)), args=cfg() + stdin_json(), stdin=src, compare=JS)

src = '{"d": {"c": {"b": {"z": 1, "a": 2}, "a": 1}, "b": 1}, "a": {"y": 1, "x": 2}}\n'
case("g3-deep", "g3.basic", "Four levels deep",
     out(expect(src)), args=cfg() + stdin_json(), stdin=src, compare=JS)

src = '{"b": 1, "a": 2}\n'
case("g3-file-in-place", "g3.io", "A .json file is rewritten in place",
     out(files={"data.json": expect(src)}),
     args=cfg() + ["{tmp}/data.json"], files={"data.json": src}, watch_files=["data.json"], compare=JF)

src = '{"version": "1.0.0", "scripts": {}, "name": "x", "license": "MIT", "description": "d"}\n'
rule = lambda p, k: {"first": ["name", "version"], "last": ["scripts"]} if k == "attrs" else {}
case("g3-first-last", "g3.config", "[attrs] first / last pin JSON keys",
     out(expect(src, rule)), args=cfg("[attrs]", 'first = ["name", "version"]', 'last = ["scripts"]') + stdin_json(),
     stdin=src, compare=JS)

src = '{"scripts": {"test": "t", "build": "b", "lint": "l"}, "name": "x", "dependencies": {"zod": "1", "axios": "1"}}\n'
rule = lambda p, k: {"sort": False} if (k == "attrs" and p == ("scripts",)) else {}
case("g3-override-path", "g3.config", "[[overrides]] path selects one JSON object",
     out(expect(src, rule)), args=cfg("[[overrides]]", 'path = "scripts"', "attrs.sort = false") + stdin_json(),
     stdin=src, compare=JS)

src_lock = '{"b": 1, "a": 2}\n'
case("g3-files-pattern", "g3.config", "[[files]] entries match .json files",
     out(files={"data.json": expect(src_lock), "locked.json": expect(src_lock, lambda p, k: {"sort": False})}),
     args=["--config-toml", OFF + '\n\n[[files]]\npattern = "locked.json"\nattrs.sort = false\n',
           "{tmp}/data.json", "{tmp}/locked.json"],
     cwd=".", files={"data.json": src_lock, "locked.json": src_lock},
     watch_files=["data.json", "locked.json"], compare=JF)

src = '{"b": 1, "a": 2}\n'
case("g3-mixed-nix-and-json", "g3.io", "Nix and JSON files in one call are both handled",
     out(files={"a.nix": "{ a = 2; b = 1; }\n", "b.json": expect(src)}),
     args=cfg() + ["{tmp}/a.nix", "{tmp}/b.json"], files={"a.nix": "{ b = 1; a = 2; }\n", "b.json": src},
     watch_files=["a.nix", "b.json"], exact_files=["a.nix"], compare=JF)

PKG = '''{
  "scripts": {"test": "vitest", "build": "tsc", "dev": "vite"},
  "dependencies": {"zod": "^3.23.0", "react": "^18.3.1", "axios": "^1.7.2"},
  "version": "0.4.1",
  "devDependencies": {"vitest": "^2.0.0", "typescript": "^5.5.0"},
  "name": "my-app",
  "private": true,
  "description": "demo",
  "files": ["dist", "README.md", "LICENSE"]
}
'''
PKG_CFG = OFF + '''
[attrs]
first = ["name", "version", "description", "private"]

[[overrides]]
path = "scripts"
attrs.sort = false
'''
rule = lambda p, k: ({"sort": False} if p == ("scripts",) else
                     ({"first": ["name", "version", "description", "private"]} if k == "attrs" else {}))
case("g3-realistic-package-json", "g3.realistic", "A package.json with a project config",
     out(files={"package.json": expect(PKG, rule)}),
     args=["{tmp}/package.json"], dirs=[".git"], files={"pedantix.toml": PKG_CFG, "package.json": PKG},
     watch_files=["package.json"], compare=JF)

TSC = '''{
  "include": ["src", "tests"],
  "compilerOptions": {
    "strict": true,
    "target": "ES2022",
    "paths": {"@/*": ["./src/*"], "#lib/*": ["./lib/*"]},
    "module": "ESNext",
    "lib": ["ES2022", "DOM"]
  },
  "exclude": ["node_modules"]
}
'''
case("g3-realistic-tsconfig", "g3.realistic", "A tsconfig.json with defaults",
     out(expect(TSC)), args=cfg() + stdin_json("tsconfig.json"), stdin=TSC, compare=JS)

src = '{"b": 1, "a": 2}\n'
case("g3-nix-only-settings", "g3.config", "Nix-only settings in the config do not break JSON",
     out(expect(src)),
     args=cfg('inherit-placement = "last"', "top-level-blank-lines = 1", "[lets]", "sort = true",
              "[attrs]", "merge = true", "flatten = true") + stdin_json(),
     stdin=src, compare=JS)

# ============================================= g2: consistency with core rules
src = '{"b": 1, "B": 2, "a": 3, "A": 4, "_c": 5}\n'
case("g2-byte-order-case", "g2.sort", "Upper case before lower case, '_' between (byte order, like Nix)",
     out(expect(src)), args=cfg() + stdin_json(), stdin=src, compare=JS)

src = '{"a10": 1, "a2": 2, "a1": 3, "a": 4}\n'
case("g2-byte-order-digits", "g2.sort", "a10 before a2 (byte order, not natural order)",
     out(expect(src)), args=cfg() + stdin_json(), stdin=src, compare=JS)

src = '{"z": 1, "été": 2, "a": 3, "Zebra": 4}\n'
case("g2-byte-order-unicode", "g2.sort", "Non-ASCII keys sort after ASCII (byte order)",
     out(expect(src)), args=cfg() + stdin_json(), stdin=src, compare=JS)

src = '{"c": 1, "enable": true, "a": 2}\n'
case("g2-sort-false-ignores-first", "g2.config", "sort = false keeps the order and ignores first",
     out(expect(src, lambda p, k: {"sort": False} if k == "attrs" else {})),
     args=cfg("[attrs]", "sort = false", 'first = ["enable"]') + stdin_json(), stdin=src, compare=JS)

src = '{"extra": 1, "b": 2, "package": 3, "zz": 4, "enable": true, "a": 5}\n'
rule = lambda p, k: {"first": ["enable", "package"], "last": ["zz", "extra"]} if k == "attrs" else {}
case("g2-first-last-listed-order", "g2.config", "first and last keep the order they are listed in",
     out(expect(src, rule)),
     args=cfg("[attrs]", 'first = ["enable", "package"]', 'last = ["zz", "extra"]') + stdin_json(),
     stdin=src, compare=JS)

src = '{"services": {"foo": {"z": 1, "description": "d", "a": 2, "nested": {"description": "x", "b": 1}}}}\n'
rule = lambda p, k: {"first": ["description"]} if (k == "attrs" and p == ("services", "foo")) else {}
case("g2-override-star-one-component", "g2.overrides", "'*' matches exactly one path component",
     out(expect(src, rule)),
     args=cfg("[[overrides]]", 'path = "services.*"', 'attrs.first = ["description"]') + stdin_json(),
     stdin=src, compare=JS)

src = '{"pkg": {"dependencies": {"y": "1", "b": "2"}}, "m": 1, "dependencies": {"z": "1", "a": "2"}}\n'
rule = lambda p, k: {"sort": False} if (k == "attrs" and p and p[-1] == "dependencies") else {}
case("g2-override-double-star", "g2.overrides", "'**' matches zero or more components",
     out(expect(src, rule)),
     args=cfg("[[overrides]]", 'path = "**.dependencies"', "attrs.sort = false") + stdin_json(),
     stdin=src, compare=JS)

src = '{"other": {"d": 1, "c": 2}, "keep": {"b": 1, "a": 2}}\n'
rule = lambda p, k: ({} if p == ("keep",) else {"sort": False}) if k == "attrs" else {}
case("g2-override-later-wins", "g2.overrides", "A later override wins over an earlier one",
     out(expect('{"keep": {"b": 1, "a": 2}, "other": {"d": 1, "c": 2}}\n', rule)),
     args=cfg("[[overrides]]", 'path = "**"', "attrs.sort = false",
              "[[overrides]]", 'path = "keep"', "attrs.sort = true") + stdin_json(),
     stdin='{"keep": {"b": 1, "a": 2}, "other": {"d": 1, "c": 2}}\n', compare=JS)

src = '{"files": ["b", "a"], "other": ["d", "c"]}\n'
rule = lambda p, k: {"sort": True} if (k == "lists" and p == ("files",)) else {}
case("g2-lists-override-path", "g2.overrides", "lists.sort for one path only",
     out(expect(src, rule)),
     args=cfg("[[overrides]]", 'path = "**.files"', "lists.sort = true") + stdin_json(), stdin=src, compare=JS)

src = '{"a": 1, "c": 2, "b": 3}\n'
LAST_A = OFF + '\n[attrs]\nlast = ["a"]\n'
last_a = lambda p, k: {"last": ["a"]} if k == "attrs" else {}
case("g2-discovered-config", "g2.discovery", "A pedantix.toml next to the .json file is used",
     out(files={"data.json": expect(src, last_a)}),
     args=["{tmp}/data.json"], dirs=[".git"], files={"pedantix.toml": LAST_A, "data.json": src},
     watch_files=["data.json"], compare=JF)
case("g2-discovered-upwards", "g2.discovery", "The config is searched upwards to the repo root",
     out(files={"a/b/data.json": expect(src, last_a)}),
     args=["{tmp}/a/b/data.json"], dirs=[".git"], files={"pedantix.toml": LAST_A, "a/b/data.json": src},
     watch_files=["a/b/data.json"], compare=JF)
case("g2-discovery-stops-at-git-root", "g2.discovery", "A config above the git root is not used",
     out(files={"repo/data.json": expect(src)}),
     args=["--formatter", "off", "{tmp}/repo/data.json"], dirs=["repo/.git"],
     files={"pedantix.toml": LAST_A, "repo/data.json": src}, watch_files=["repo/data.json"], compare=JF)
case("g2-xdg-global-config", "g2.discovery", "$XDG_CONFIG_HOME/pedantix/pedantix.toml applies to JSON",
     out(files={"proj/data.json": expect(src, last_a)}),
     args=["{tmp}/proj/data.json"], dirs=["proj/.git"], env={"XDG_CONFIG_HOME": "{tmp}/xdg"},
     files={"xdg/pedantix/pedantix.toml": LAST_A, "proj/data.json": src}, watch_files=["proj/data.json"], compare=JF)
case("g2-set-flag", "g2.config", "--set works for JSON too",
     out(expect(src, last_a)), args=cfg() + ["--set", 'attrs.last=["a"]'] + stdin_json(), stdin=src, compare=JS)

src = '{"b": 1, "a": 2}\n'
FILES_CFG = OFF + '\n\n[[files]]\npattern = "*.lock.json"\nattrs.sort = false\n'
case("g2-files-pattern-discovered", "g2.discovery", "[[files]] in a discovered config select .json files",
     out(files={"data.json": expect(src), "deps.lock.json": src}),
     args=["{tmp}/data.json", "{tmp}/deps.lock.json"], dirs=[".git"],
     files={"pedantix.toml": FILES_CFG, "data.json": src, "deps.lock.json": src},
     watch_files=["data.json", "deps.lock.json"], compare=JF)
case("g2-stdin-filepath-files", "g2.discovery", "--stdin-filepath selects [[files]] entries for JSON stdin",
     out(expect(src, lambda p, k: {"sort": False})),
     args=["--stdin-filepath", "{tmp}/deps.lock.json"], dirs=[".git"],
     files={"pedantix.toml": FILES_CFG}, stdin=src, compare=JS)

src = '{"b": 1, "a": 2}\n'
case("g2-check-file-dirty", "g2.cli", "--check on an unsorted .json file: exit 1, file untouched, file named",
     out(files={"dirty.json": src}, exit=1),
     args=cfg() + ["--check", "{tmp}/dirty.json"], files={"dirty.json": src},
     watch_files=["dirty.json"], exact_files=["dirty.json"], stderr_contains=["dirty.json"],
     compare=["exit", "stdout"])
case("g2-check-stdin-dirty", "g2.cli", "--check on unsorted JSON stdin: exit 1, nothing on stdout",
     out(exit=1), args=cfg() + ["--check"] + stdin_json(), stdin=src, compare=["exit", "stdout"])
case("g2-file-mode-silent", "g2.cli", "File mode prints nothing on stdout",
     out(files={"data.json": expect(src)}), args=cfg() + ["{tmp}/data.json"], files={"data.json": src},
     watch_files=["data.json"], compare=JF)

bad = '{"b": 1, "a": }\n'
case("g2-invalid-json-stdin", "g2.errors", "Invalid JSON exits with 2 and prints nothing",
     out(exit=2), args=cfg() + stdin_json(), stdin=bad, compare=["exit", "stdout"])
case("g2-invalid-json-file-untouched", "g2.errors", "An invalid .json file is not modified",
     out(files={"bad.json": bad}, exit=2), args=cfg() + ["{tmp}/bad.json"], files={"bad.json": bad},
     watch_files=["bad.json"], exact_files=["bad.json"], compare=["exit", "stdout"])
case("g2-unknown-config-key", "g2.errors", "Unknown config keys are still rejected when formatting JSON",
     out(exit=2), args=cfg("[attrs]", "colour = true") + stdin_json(), stdin=src, compare=["exit", "stdout"])
case("g2-wrong-value-type", "g2.errors", "A wrongly typed config value is still rejected",
     out(exit=2), args=cfg("[attrs]", 'sort = "yes"') + stdin_json(), stdin=src, compare=["exit", "stdout"])


# ----------------------------------------------------------------------- write
cases_dir, exp_dir = HERE / "cases", HERE / "expected"
for d in (cases_dir, exp_dir):
    d.mkdir(exist_ok=True)
    for old in d.glob("*.json"):
        old.unlink()
for i, (c, e) in enumerate(CASES, 1):
    (cases_dir / f"{i:03d}-{c['id']}.json").write_text(json.dumps(c, indent=2, ensure_ascii=False) + "\n")
    entry = {"id": c["id"], "valid": True, "problems": [], "source": "hand-written",
             "exit": e["exit"], "stdout": e["stdout"], "files": e["files"]}
    (exp_dir / f"{c['id']}.json").write_text(json.dumps(entry, indent=2, ensure_ascii=False) + "\n")
g2 = sum(1 for c, _ in CASES if c["feature"].startswith("g2"))
print(f"wrote {len(CASES)} cases ({g2} in g2, {len(CASES) - g2} in g3)")
