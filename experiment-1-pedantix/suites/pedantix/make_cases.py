#!/usr/bin/env python3
"""Generates the pedantix contract cases (cases/*.json).

Design rules for every case:
- The base formatter is switched off (`formatter = "off"` or `--formatter off`),
  so no external formatter (nixfmt, alejandra) is needed and the contract binds
  pedantix's own behaviour only.
- Where a base formatter is needed, only POSIX tools (cat, sed, sh) are used.
- What is compared: exit code, stdout, and watched files. stderr wording is
  incidental; only a few hand-picked words are required.
"""

import json
from pathlib import Path

OFF = 'formatter = "off"'
CASES = []


def case(id, feature, desc, **kw):
    c = {"id": id, "feature": feature, "desc": desc}
    c.update(kw)
    CASES.append(c)


def cfg(*lines):
    """--config-toml with the formatter off plus extra TOML lines."""
    return ["--config-toml", "\n".join([OFF, *lines])]


# ---------------------------------------------------------------- CLI / IO
case("cli-stdin-basic", "cli.io", "No files: read stdin, write the result to stdout",
     args=cfg(), stdin="{ b = 1; a = 2; }\n", idempotent=True)
case("cli-stdin-dash", "cli.io", "A single '-' also means stdin",
     args=cfg() + ["-"], stdin="{ b = 1; a = 2; }\n")
case("cli-check-stdin-dirty", "cli.check", "--check on stdin that would change: exit 1, nothing on stdout",
     args=cfg() + ["--check"], stdin="{ b = 1; a = 2; }\n")
case("cli-check-stdin-clean", "cli.check", "--check on already formatted stdin: exit 0",
     args=cfg() + ["--check"], stdin="{ a = 2; b = 1; }\n")
case("cli-files-in-place", "cli.io", "Files are rewritten in place",
     args=cfg() + ["{tmp}/one.nix", "{tmp}/two.nix"],
     files={"one.nix": "{ b = 1; a = 2; }\n", "two.nix": "{ d = 1; c = 2; }\n"},
     watch_files=["one.nix", "two.nix"])
case("cli-files-check", "cli.check", "--check on files: exit 1, files untouched, the dirty file is named",
     args=cfg() + ["--check", "{tmp}/dirty.nix", "{tmp}/clean.nix"],
     files={"dirty.nix": "{ b = 1; a = 2; }\n", "clean.nix": "{ a = 1; b = 2; }\n"},
     watch_files=["dirty.nix", "clean.nix"], stderr_contains=["dirty.nix"])
case("cli-files-already-clean", "cli.io", "A file that needs no change is left as is, exit 0",
     args=cfg() + ["{tmp}/f.nix"], files={"f.nix": "{ a = 1; b = 2; }\n"}, watch_files=["f.nix"])
case("cli-invalid-nix", "cli.errors", "Invalid Nix exits with 2",
     args=cfg(), stdin="{ a = ; }\n")
case("cli-invalid-nix-file-untouched", "cli.errors", "Invalid Nix file is not modified",
     args=cfg() + ["{tmp}/bad.nix"], files={"bad.nix": "{ b = 1; a = ; }\n"}, watch_files=["bad.nix"])
case("cli-on-parse-error-skip", "cli.errors", "on-parse-error = skip passes unparsable input through",
     args=cfg('on-parse-error = "skip"'), stdin="{ b = [ 1 2 ] |> f; a = 1; }\n")
case("cli-on-parse-error-skip-runs-formatter", "cli.errors", "With skip, only the base formatter runs",
     args=["--config-toml", 'on-parse-error = "skip"\nformatter-command = ["tr", "a-z", "A-Z"]\nformat-before-sort = false'],
     stdin="{ b = [ 1 2 ] |> f; a = 1; }\n")
case("cli-config-conflict", "cli.errors", "--config and --config-toml cannot be combined",
     args=["--config", "{tmp}/p.toml", "--config-toml", OFF], stdin="{ a = 1; }\n",
     files={"p.toml": OFF + "\n"}, compare=["exit", "stdout"])
case("cli-missing-file", "cli.errors", "A file that does not exist is an error (exit 2)",
     args=cfg() + ["{tmp}/nope.nix"], compare=["exit", "stdout"])
case("cli-unknown-config-key", "config.errors", "Unknown keys in a section are rejected",
     args=cfg("[attrs]", "colour = true"), stdin="{ a = 1; }\n", compare=["exit", "stdout"])
case("cli-invalid-toml", "config.errors", "Invalid TOML is rejected",
     args=["--config-toml", "formatter = "], stdin="{ a = 1; }\n", compare=["exit", "stdout"])
case("cli-version", "cli.io", "--version exits 0", args=["--version"], compare=["exit"])

# ------------------------------------------------------- config discovery
case("cfg-discovered", "config.discovery", "pedantix.toml next to the file is used",
     args=["{tmp}/f.nix"], dirs=[".git"],
     files={"pedantix.toml": OFF + "\n[attrs]\nlast = [\"a\"]\n", "f.nix": "{ a = 1; c = 2; b = 3; }\n"},
     watch_files=["f.nix"])
case("cfg-discovered-hidden-name", "config.discovery", ".pedantix.toml is found too",
     args=["{tmp}/f.nix"], dirs=[".git"],
     files={".pedantix.toml": OFF + "\n[attrs]\nlast = [\"a\"]\n", "f.nix": "{ a = 1; c = 2; b = 3; }\n"},
     watch_files=["f.nix"])
case("cfg-discovered-upwards", "config.discovery", "Config is searched upwards to the repo root",
     args=["{tmp}/a/b/f.nix"], dirs=[".git"],
     files={"pedantix.toml": OFF + "\n[attrs]\nlast = [\"a\"]\n", "a/b/f.nix": "{ a = 1; c = 2; b = 3; }\n"},
     watch_files=["a/b/f.nix"])
case("cfg-discovery-stops-at-git-root", "config.discovery", "A config above the git root is not used",
     args=["--formatter", "off", "{tmp}/repo/f.nix"], dirs=["repo/.git"],
     files={"pedantix.toml": OFF + "\n[attrs]\nsort = false\n", "repo/f.nix": "{ b = 1; a = 2; }\n"},
     watch_files=["repo/f.nix"])
case("cfg-per-directory", "config.discovery", "Each directory uses its own discovered config",
     args=["{tmp}/a/f.nix", "{tmp}/b/f.nix"], dirs=["a/.git", "b/.git"],
     files={"a/pedantix.toml": OFF + "\n", "b/pedantix.toml": OFF + "\n[attrs]\nsort = false\n",
            "a/f.nix": "{ b = 1; a = 2; }\n", "b/f.nix": "{ b = 1; a = 2; }\n"},
     watch_files=["a/f.nix", "b/f.nix"])
case("cfg-explicit-path", "config.discovery", "--config names the config file explicitly",
     args=["--config", "{tmp}/conf/x.toml", "{tmp}/f.nix"],
     files={"conf/x.toml": OFF + "\n[attrs]\nlast = [\"a\"]\n", "f.nix": "{ a = 1; c = 2; b = 3; }\n"},
     watch_files=["f.nix"])
case("cfg-config-toml-disables-discovery", "config.discovery", "--config-toml ignores pedantix.toml files",
     args=cfg() + ["{tmp}/f.nix"], dirs=[".git"],
     files={"pedantix.toml": OFF + "\n[attrs]\nsort = false\n", "f.nix": "{ b = 1; a = 2; }\n"},
     watch_files=["f.nix"])
case("cfg-xdg-global", "config.discovery", "Without a local config, $XDG_CONFIG_HOME/pedantix/pedantix.toml is used",
     args=["{tmp}/proj/f.nix"], dirs=["proj/.git"], env={"XDG_CONFIG_HOME": "{tmp}/xdg"},
     files={"xdg/pedantix/pedantix.toml": OFF + "\n[attrs]\nlast = [\"a\"]\n", "proj/f.nix": "{ a = 1; c = 2; b = 3; }\n"},
     watch_files=["proj/f.nix"])
case("cfg-set-overrides", "config.set", "--set changes one key on top of the loaded config",
     args=cfg() + ["--set", "lets.sort=false"], stdin="let\n  b = 1;\n  a = 2;\nin\n{ y = a; x = b; }\n")
case("cfg-set-array", "config.set", "--set values are parsed as TOML",
     args=cfg() + ["--set", 'attrs.first=["z"]'], stdin="{ a = 1; z = 2; m = 3; }\n")
case("cfg-set-files-entry", "config.set", "--set can add [[files]] entries",
     args=cfg() + ["--set", 'files=[{pattern="*.nix", attrs.last=["a"]}]', "{tmp}/f.nix"],
     files={"f.nix": "{ a = 1; c = 2; b = 3; }\n"}, watch_files=["f.nix"])
case("cfg-files-patterns", "config.files", "[[files]] entries configure matching files only",
     args=["{tmp}/module.nix", "{tmp}/hello.pkg.nix", "{tmp}/pkgs/nested.nix"], dirs=[".git"],
     files={"pedantix.toml": OFF + '\n\n[[files]]\npattern = "*.pkg.nix"\nattrs.sort = false\n\n[[files]]\npattern = "pkgs/*.nix"\nattrs.first = ["b"]\n',
            "module.nix": "{ b = 1; a = 2; }\n", "hello.pkg.nix": "{ b = 1; a = 2; }\n", "pkgs/nested.nix": "{ b = 1; a = 2; }\n"},
     watch_files=["module.nix", "hello.pkg.nix", "pkgs/nested.nix"])
case("cfg-files-cwd-anchored", "config.files", "'./' anchors a pattern at the working directory",
     args=["--config-toml", OFF + '\n\n[[files]]\npattern = "./*.nix"\nattrs.sort = false\n', "top.nix", "pkgs/nested.nix"],
     files={"top.nix": "{ b = 1; a = 2; }\n", "pkgs/nested.nix": "{ b = 1; a = 2; }\n"},
     watch_files=["top.nix", "pkgs/nested.nix"])
case("cfg-stdin-filepath-files", "config.files", "--stdin-filepath selects [[files]] entries for stdin",
     args=["--stdin-filepath", "{tmp}/hello.pkg.nix"], dirs=[".git"], stdin="{ a = 1; c = 2; b = 3; }\n",
     files={"pedantix.toml": OFF + '\n\n[[files]]\npattern = "*.pkg.nix"\nattrs.last = ["a"]\n'})
case("cfg-warning-ignored-key", "config.warnings", "A key with no effect warns but still formats",
     args=["{tmp}/f.nix"], dirs=[".git"],
     files={"pedantix.toml": OFF + "\n\n[lets]\nmerge = true\n", "f.nix": "{ b = 1; a = 2; }\n"},
     watch_files=["f.nix"], stderr_contains=["lets.merge"])
case("cfg-preset-nixos-module", "config.presets", "preset = nixos-module orders module arguments",
     args=cfg('preset = "nixos-module"'), stdin="{ pkgs, lib, config, ... }:\n{ b = 1; a = 2; }\n")
case("cfg-preset-nixpkgs-package", "config.presets", "preset = nixpkgs-package orders a derivation",
     args=cfg('preset = "nixpkgs-package"'),
     stdin='{ stdenv, lib, fetchurl }:\nstdenv.mkDerivation {\n  version = "1.0";\n  src = fetchurl { url = "u"; hash = "h"; };\n  meta = { license = lib.licenses.mit; description = "d"; };\n  pname = "hello";\n  buildInputs = [ ];\n}\n')
case("cfg-preset-alphabetical", "config.presets", "preset = alphabetical",
     args=cfg('preset = "alphabetical"'), stdin="{ pkgs, lib, ... }:\n{ imports = [ ]; b = 1; enable = true; a = 2; }\n")
case("cfg-preset-explicit-wins", "config.presets", "Explicit settings win over the preset",
     args=cfg('preset = "nixos-module"', "[args]", 'first = ["pkgs"]'), stdin="{ lib, pkgs, config, ... }:\n{ }\n")
case("cfg-preset-unknown", "config.errors", "An unknown preset is an error",
     args=cfg('preset = "nope"'), stdin="{ a = 1; }\n", compare=["exit", "stdout"])

# ------------------------------------------------- base formatter / safety
case("fmt-command-cat", "formatter", "formatter-command runs as a stdin->stdout filter",
     args=["--config-toml", 'formatter-command = ["cat"]'], stdin="{ b = 1; a = 2; }\n")
case("fmt-flag-overrides-command", "formatter", "--formatter off overrides a broken formatter-command",
     args=["--config-toml", 'formatter-command = ["pedantix-missing-base-formatter"]', "--formatter", "off"],
     stdin="{ b = 1; a = 2; }\n")
case("fmt-missing-command", "formatter", "A missing base formatter is an error",
     args=["--config-toml", 'formatter-command = ["pedantix-missing-base-formatter"]'], stdin="{ a = 1; }\n",
     compare=["exit", "stdout"])
case("fmt-failing-command", "formatter", "A base formatter that fails is an error",
     args=["--config-toml", 'formatter-command = ["false"]'], stdin="{ a = 1; }\n", compare=["exit", "stdout"])
case("fmt-content-change-refused", "formatter.safety", "A base formatter that changes content is refused",
     args=["--config-toml", 'formatter-command = ["sh", "-c", "cat >/dev/null; printf \'{ zzz = 9; }\\\\n\'"]'],
     stdin="{ b = 1; a = 2; }\n", compare=["exit", "stdout"])
case("fmt-passes-both", "formatter", "Formatter runs before and after sorting by default",
     args=["--config-toml", 'formatter-command = ["sed", "s/$/ /"]'], stdin="{ b = 1; a = 2; }\n")
case("fmt-no-before", "formatter", "format-before-sort = false",
     args=["--config-toml", 'formatter-command = ["sed", "s/$/ /"]\nformat-before-sort = false'], stdin="{ b = 1; a = 2; }\n")
case("fmt-no-after", "formatter", "format-after-sort = false",
     args=["--config-toml", 'formatter-command = ["sed", "s/$/ /"]\nformat-after-sort = false'], stdin="{ b = 1; a = 2; }\n")
case("fmt-discovered-command-refused", "formatter.safety", "formatter-command from a discovered config is not executed",
     args=["{tmp}/f.nix"], files={"pedantix.toml": 'formatter-command = ["cat"]\n', "f.nix": "{ b = 1; a = 2; }\n"},
     watch_files=["f.nix"], stderr_contains=["--allow-formatter-command"])
case("fmt-discovered-command-allowed", "formatter.safety", "--allow-formatter-command runs it",
     args=["--allow-formatter-command", "{tmp}/f.nix"],
     files={"pedantix.toml": 'formatter-command = ["cat"]\n', "f.nix": "{ b = 1; a = 2; }\n"}, watch_files=["f.nix"])
case("fmt-discovered-files-entry-command-refused", "formatter.safety", "A [[files]] formatter-command in a discovered config is refused too",
     args=["{tmp}/f.nix"],
     files={"pedantix.toml": OFF + '\n\n[[files]]\npattern = "*.nix"\nformatter-command = ["cat"]\n', "f.nix": "{ b = 1; a = 2; }\n"},
     watch_files=["f.nix"])
case("fmt-xdg-command-allowed", "formatter.safety", "formatter-command from the global XDG config is executed",
     args=["{tmp}/proj/f.nix"], dirs=["proj/.git"], env={"XDG_CONFIG_HOME": "{tmp}/xdg"},
     files={"xdg/pedantix/pedantix.toml": 'formatter-command = ["cat"]\n', "proj/f.nix": "{ b = 1; a = 2; }\n"},
     watch_files=["proj/f.nix"])

# ------------------------------------------------------------- attrs sort
case("attrs-nested", "sort.attrs", "Nested sets are sorted at every level",
     args=cfg(), stdin="{\n  b = {\n    z = 1;\n    y = 2;\n  };\n  a = 1;\n}\n", idempotent=True)
case("attrs-case-sensitive", "sort.attrs", "Upper and lower case names",
     args=cfg(), stdin="{ b = 1; B = 2; a = 3; A = 4; _c = 5; }\n", idempotent=True)
case("attrs-digits", "sort.attrs", "Names with digits",
     args=cfg(), stdin="{ a10 = 1; a2 = 2; a1 = 3; a = 4; }\n", idempotent=True)
case("attrs-quoted-names", "sort.attrs", "Quoted names sort by their content",
     args=cfg(), stdin='{ "b" = 1; a = 2; "c d" = 3; "A" = 4; }\n', idempotent=True)
case("attrs-attrpaths", "sort.attrs", "Dotted attrpaths sort component by component",
     args=cfg(), stdin="{ b.x = 1; a.z = 2; a.y = 3; a = { }; }\n", idempotent=True)
case("attrs-comments-move", "sort.attrs", "Comments stay with their binding",
     args=cfg(), stdin="{\n  # about b\n  b = 1;\n  a = 2; # trailing a\n}\n", idempotent=True)
case("attrs-blank-lines-kept", "sort.attrs", "Blank lines and comments when reordering",
     args=cfg(), stdin="{\n  c = 3;\n\n  # second group\n  b = 2;\n  a = 1;\n}\n", idempotent=True)
case("attrs-multiline-values", "sort.attrs", "Multi-line values move intact",
     args=cfg(), stdin="{\n  b = ''\n    line one\n    line two\n  '';\n  a = [\n    1\n    2\n  ];\n}\n", idempotent=True)
case("attrs-rec", "sort.attrs", "rec sets are sorted too",
     args=cfg(), stdin="rec { b = a; a = 1; }\n", idempotent=True)
case("attrs-dynamic-key", "sort.attrs", "Interpolated keys",
     args=cfg(), stdin='{ b = 1; ${name} = 2; a = 3; "x${y}" = 4; }\n', idempotent=True)
case("attrs-first-last", "sort.attrs", "attrs.first / attrs.last pin names",
     args=cfg("[attrs]", 'first = ["enable", "package"]', 'last = ["zz", "extra"]'),
     stdin="{ extra = 1; b = 2; package = 3; zz = 4; enable = true; a = 5; }\n", idempotent=True)
case("attrs-sort-false-with-first", "sort.attrs", "sort = false with first",
     args=cfg("[attrs]", "sort = false", 'first = ["enable"]'), stdin="{ c = 1; enable = true; a = 2; }\n")
case("attrs-sort-false", "sort.attrs", "attrs.sort = false keeps order",
     args=cfg("[attrs]", "sort = false"), stdin="{ c = 1; a = 2; b = 3; }\n")
case("attrs-in-function-call", "sort.attrs", "Sets passed to function calls are sorted",
     args=cfg(), stdin='pkgs.mkShell { packages = [ ]; name = "x"; buildInputs = [ ]; }\n', idempotent=True)
case("attrs-single-line-kept", "sort.attrs", "A single-line set stays on one line",
     args=cfg(), stdin="{ x = { c = 1; b = 2; a = 3; }; }\n", idempotent=True)

# ------------------------------------------------------------------ args
case("args-basic", "sort.args", "Function arguments are sorted",
     args=cfg(), stdin="{ pkgs, lib, config }:\nlib\n", idempotent=True)
case("args-defaults", "sort.args", "Arguments with defaults",
     args=cfg(), stdin="{ z ? 1, pkgs, a ? null, lib, ... }:\nlib\n", idempotent=True)
case("args-first-last-defaulted", "sort.args", "<defaulted> and ... in args.last",
     args=cfg("[args]", 'first = ["self", "lib", "config", "pkgs"]', 'last = ["<defaulted>", "..."]'),
     stdin="{ z ? 1, foo, pkgs, a ? null, lib, self, ... }:\nlib\n", idempotent=True)
case("args-multiline-comments", "sort.args", "Multi-line formals with comments",
     args=cfg(), stdin="{\n  pkgs,\n  # the library\n  lib,\n  config, # cfg\n  ...\n}:\n{ }\n", idempotent=True)
case("args-at-pattern", "sort.args", "Formals with an @ binding",
     args=cfg(), stdin="args@{ pkgs, lib, ... }:\nlib\n", idempotent=True)
case("args-sort-false", "sort.args", "args.sort = false",
     args=cfg("[args]", "sort = false"), stdin="{ pkgs, lib }:\nlib\n")

# ------------------------------------------------------------------ lets
case("lets-basic", "sort.lets", "let bindings are not sorted by default",
     args=cfg(), stdin="let\n  b = 1;\n  a = 2;\nin\n{ y = a; x = b; }\n")
case("lets-sort-true", "sort.lets", "lets.sort = true",
     args=cfg("[lets]", "sort = true"), stdin="let\n  c = 3;\n  b = 1;\n  a = 2;\nin\na + b + c\n", idempotent=True)
case("lets-first", "sort.lets", "lets.first",
     args=cfg("[lets]", "sort = true", 'first = ["cfg"]'), stdin="let\n  b = 1;\n  cfg = 2;\n  a = 3;\nin\nb\n")

# -------------------------------------------------------------- inherits
case("inherit-names-sorted", "sort.inherits", "Names inside inherit are sorted",
     args=cfg("[inherits]", "sort = true"), stdin="{ inherit (pkgs) c a b; z = 1; }\n", idempotent=True)
case("inherit-placement-front", "sort.inherits", "inherit lines go first by default",
     args=cfg(), stdin="{ z = 1; inherit b; a = 2; inherit (pkgs) y; }\n", idempotent=True)
case("inherit-placement-last", "sort.inherits", "inherit-placement = last",
     args=cfg('inherit-placement = "last"'), stdin="{ z = 1; inherit b; a = 2; }\n")
case("inherit-placement-sorted", "sort.inherits", "inherit-placement = sorted",
     args=cfg('inherit-placement = "sorted"'), stdin="{ z = 1; inherit b; a = 2; }\n")
case("inherit-placement-first-invalid", "config.errors", "'first' is rejected although the example config lists it",
     args=cfg('inherit-placement = "first"'), stdin="{ z = 1; inherit b; a = 2; }\n", compare=["exit", "stdout"])
case("inherit-multiple-groups", "sort.inherits", "Several inherit statements",
     args=cfg("[inherits]", "sort = true"), stdin="{ inherit (lib) mkIf mkDefault; inherit c b; x = 1; }\n")

# ------------------------------------------------------------------ lists
case("lists-default-unsorted", "sort.lists", "Lists are not sorted by default",
     args=cfg(), stdin='{ xs = [ "b" "a" "c" ]; }\n')
case("lists-sort-true", "sort.lists", "lists.sort = true",
     args=cfg("[lists]", "sort = true"), stdin='{ xs = [ "b" "a" "c" ]; ys = [ pkgs.z pkgs.a ]; }\n', idempotent=True)
case("lists-sort-comments", "sort.lists", "Comments move with list elements",
     args=cfg("[lists]", "sort = true"), stdin="[\n  # bee\n  b\n  a # ay\n  c\n]\n", idempotent=True)
case("lists-override-path", "overrides", "lists.sort for one path only",
     args=cfg("[[overrides]]", 'path = "**.environment.systemPackages"', "lists.sort = true"),
     stdin="{\n  environment.systemPackages = [ pkgs.vim pkgs.git ];\n  other = [ b a ];\n}\n")

# ------------------------------------------------------------ overrides
case("overrides-star-one-component", "overrides", "* matches exactly one path component",
     args=cfg("[[overrides]]", 'path = "systemd.services.*"', 'attrs.first = ["description", "wantedBy"]'),
     stdin='{ systemd.services.foo = { serviceConfig = { }; wantedBy = [ ]; description = "d"; after = [ ]; }; }\n')
case("overrides-double-star", "overrides", "** matches any depth",
     args=cfg("[[overrides]]", 'path = "**.settings.alias"', "attrs.sort = false"),
     stdin='{ programs.git.settings.alias = { c = "commit"; a = "add"; }; z.settings.alias = { y = 1; x = 2; }; b = 1; a = 2; }\n')
case("overrides-later-wins", "overrides", "Later overrides win over earlier ones",
     args=cfg("[[overrides]]", 'path = "**"', "attrs.sort = false", "[[overrides]]", 'path = "keep"', "attrs.sort = true"),
     stdin="{ keep = { b = 1; a = 2; }; other = { d = 1; c = 2; }; }\n")

# --------------------------------------------------------- merge/flatten
case("merge-basic", "attrs.merge", "merge combines bindings that share a first component",
     args=cfg("[attrs]", "merge = true"),
     stdin='{\n  programs.emacs.enable = true;\n  services.foo.port = 1;\n  programs.kitty.enable = true;\n  services.foo.address = "::";\n}\n', idempotent=True)
case("merge-with-existing-set", "attrs.merge", "merge into an existing nested set",
     args=cfg("[attrs]", "merge = true"), stdin="{ a.b = 1; a = { c = 2; }; }\n")
case("merge-off-by-default", "attrs.merge", "No merging without merge = true",
     args=cfg(), stdin="{ a.c = 1; b = 2; a.b = 3; }\n")
case("flatten-basic", "attrs.flatten", "flatten collapses single-binding sets",
     args=cfg("[attrs]", "flatten = true"), stdin="{\n  a = {\n    b = {\n      c = 1;\n    };\n  };\n  d = {\n    e = 2;\n    f = 3;\n  };\n}\n", idempotent=True)
case("flatten-and-merge", "attrs.merge", "merge and flatten together",
     args=cfg("[attrs]", "merge = true", "flatten = true"), stdin="{ x = { y = 1; }; a.b = 1; a.c = 2; }\n", idempotent=True)

# ------------------------------------------------------------ name style
case("names-identifier", "names", "name-style = identifier unquotes valid identifiers",
     args=cfg("[attrs]", 'name-style = "identifier"'),
     stdin='{\n  "valid" = true;\n  "not valid" = false;\n  "kebab-case" = true;\n  "if" = false;\n}\n', idempotent=True)
case("names-string", "names", "name-style = string quotes every name",
     args=cfg("[attrs]", 'name-style = "string"'), stdin="{ b = 1; a = 2; }\n", idempotent=True)
case("names-override", "names", "name-style per path with flatten",
     args=cfg("[attrs]", "flatten = true", 'name-style = "identifier"', "[[overrides]]", 'path = "**.users.users"', 'attrs.name-style = "string"'),
     stdin="{\n  users.users = {\n    bob = {\n      isNormalUser = true;\n    };\n  };\n}\n")
case("names-inherits-identifier", "names", "name-style on inherits",
     args=cfg("[inherits]", "sort = true", 'name-style = "identifier"'), stdin='{ inherit "b" a; }\n')

# --------------------------------------------------------------- spacing
SPACING_SRC = "{\n  b = 2;\n\n\n  a = 1;\n  c = { y = 2; x = 1; };\n}\n"
for n in (0, 1, 2):
    case(f"spacing-top-level-{n}", "spacing", f"top-level-blank-lines = {n}",
         args=cfg(f"top-level-blank-lines = {n}"), stdin=SPACING_SRC, idempotent=True)
case("spacing-mode-all", "spacing", "top-level-blank-lines-mode = all",
     args=cfg("top-level-blank-lines = 1", 'top-level-blank-lines-mode = "all"'), stdin=SPACING_SRC, idempotent=True)
case("spacing-depth-2", "spacing", "top-level-blank-lines-depth = 2",
     args=cfg("top-level-blank-lines = 1", "top-level-blank-lines-depth = 2", 'top-level-blank-lines-mode = "all"'),
     stdin="{\n  a = {\n    y = 1;\n    x = 2;\n  };\n  b = 3;\n}\n", idempotent=True)
case("spacing-attrs-blank-lines", "spacing", "[attrs] blank-lines applies at any depth",
     args=cfg("[attrs]", "blank-lines = 1", 'blank-lines-mode = "all"'),
     stdin="{\n  a = {\n    y = 1;\n    x = 2;\n  };\n  b = 3;\n}\n", idempotent=True)
case("spacing-override-off", "spacing", "blank-lines-mode = off for one path",
     args=cfg("[attrs]", "blank-lines = 1", 'blank-lines-mode = "all"', "[[overrides]]", 'path = "a"', 'attrs.blank-lines-mode = "off"'),
     stdin="{\n  a = {\n    y = 1;\n    x = 2;\n  };\n  b = 3;\n}\n")
case("spacing-flake-outputs", "spacing", "In flake.nix, the outputs body counts as top-level",
     args=["--stdin-filepath", "{tmp}/flake.nix"], dirs=[".git"],
     files={"pedantix.toml": OFF + "\ntop-level-blank-lines = 1\n"},
     stdin="{\n  outputs =\n    { self }:\n    {\n      p = 1;\n      q = {\n        r = 2;\n      };\n    };\n}\n")
case("spacing-non-flake", "spacing", "The same input as module.nix is not spaced",
     args=["--stdin-filepath", "{tmp}/module.nix"], dirs=[".git"],
     files={"pedantix.toml": OFF + "\ntop-level-blank-lines = 1\n"},
     stdin="{\n  outputs =\n    { self }:\n    {\n      p = 1;\n      q = {\n        r = 2;\n      };\n    };\n}\n")

# ------------------------------------------------------ realistic inputs
EXAMPLE = Path(__file__).with_name("example.nix")
if EXAMPLE.exists():
    ex = EXAMPLE.read_text()
    case("example-default", "realistic", "The project's example.nix with defaults", args=cfg(), stdin=ex, idempotent=True)
    case("example-repo-config", "realistic", "example.nix with the project's own pedantix.toml (formatter off)",
         args=["--config", "{tmp}/pedantix.toml", "--formatter", "off"], stdin=ex,
         files={"pedantix.toml": Path(__file__).with_name("pedantix.repo.toml").read_text()}, idempotent=True)
    case("example-merge-flatten", "realistic", "example.nix with merge and flatten",
         args=cfg("[attrs]", "merge = true", "flatten = true"), stdin=ex)

out = Path(__file__).with_name("cases")
out.mkdir(exist_ok=True)
for old in out.glob("*.json"):
    old.unlink()
for i, c in enumerate(CASES, 1):
    (out / f"{i:03d}-{c['id']}.json").write_text(json.dumps(c, indent=2, ensure_ascii=False) + "\n")
print(f"wrote {len(CASES)} cases")
