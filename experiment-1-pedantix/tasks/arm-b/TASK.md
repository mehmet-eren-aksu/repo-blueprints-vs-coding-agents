# Task

This folder is a copy of the repo of a tool called `pedantix`. The user's request is:

> pedantix only edits Nix files today. I'd like it to also sort the object keys in JSON files. For `.json` files, and when `--stdin-filepath` points to a `.json` path, pedantix should use the same config: `[attrs]` settings apply to JSON objects, `[lists]` settings to JSON arrays, and `[[overrides]]` and `[[files]]` work too. Numbers and strings must be preserved exactly. Nix behaviour must not change at all.

The `blueprint/` folder at the repo root is an adaptation map of this code base. Read `blueprint/README.md` first, and `blueprint/map.yaml` for details, then start working.

## Working rules

1. Make your changes in this folder.
2. Do not go online. The only exception: downloading dependencies from crates.io with `cargo` is allowed.
3. Do not read files outside this folder.
4. Do not ask questions; nobody will answer in this session. If something is ambiguous, choose the most reasonable interpretation and write it in `NOTES.md`.

## When you finish

- `cargo build --release` must succeed.
- The repo's existing tests (`cargo test`) must pass.
- Write `NOTES.md` at the repo root with:
  1. The files you changed and added.
  2. The points you found ambiguous and the interpretation you chose for each.
  3. Anything you are unsure of or could not finish.
  4. Roughly how many steps and how long it took you.

If you hit the usage limit, write in `NOTES.md` where you stopped before you stop.
