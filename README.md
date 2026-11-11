# Do code maps help coding agents adapt real repos?

A small A/B experiment, and why I stopped the project.

**TL;DR.** I built *Blueprint*: an agent reads a repository and writes a code-verified "adaptation map" (core vs. domain-specific modules, extension points, invariants with `file:line` evidence). The idea was that a coding agent given this map would adapt the repo with fewer hidden breakages. I tested it in two experiments, the second on a real pull request merged after the models' knowledge cutoff, with the maintainers' own tests as hidden acceptance tests. **The map made no measurable difference.** Strong agents solved the tasks without it, and the only differences with a weaker model were noise. The result agrees with recent studies of `AGENTS.md`-style context files (see [Related work](#related-work)).

## Results

| Experiment | Model | Arm A: repo only | Arm B: repo + map |
|---|---|---|---|
| pedantix: add JSON support (1 pair) | Opus 5.5 | 40/40, 0 regressions, 6 min | 40/40, 0 regressions, 5.5 min |
| sqlfluff PR #8580 (1 pair) | Opus 5.5 | 18/18, 0 regressions, 8 min | 18/18, 0 regressions, 10.5 min |
| sqlfluff PR #8580 (3 pairs) | Haiku 5.5 | 52/54, 0 regressions, 12.0 min avg | 53/54, 0 regressions, 9.7 min avg |

Every failure in the table is the same test (`fill_alone`). Arm A failed it in 2 of 3 Haiku runs and arm B in 1. The map contains nothing about that behaviour, and the one passing arm B run whose notes I checked justified its choice from the task text, not the map. Per-run data is in [`results/runs.csv`](results/runs.csv).

## The idea

People want to adapt popular repos to their own needs: "make this PDF tool handle JPGs", "make this Nix sorter handle Python". The hypothesis was that the hard part is not writing the new code but not breaking the repo's undocumented rules, and that a map of those rules would help.

An earlier version of the project tried to regenerate a tool from its documentation alone. A docs-only rewrite of [pedantix](https://github.com/Swarsel/pedantix) passed 91.8% of black-box contract tests. The remaining 8% were exactly the hidden rules someone changing the code would trip over, which is what led to the map idea.

## Method

- **Two arms, same model.** Each arm is a fresh Claude Code session with the same model and effort level. Both get the same task text. Arm B's task has one extra paragraph pointing to the `blueprint/` folder. Because both arms use the same model, memorization of the repo affects both equally.
- **Task-blind extraction.** The map is written by a separate session that never sees the task, using a generic [`/extract` skill](extract-skill/SKILL.md). I checked each map for task-specific hints and spot-checked its `file:line` pointers against the code.
- **Isolation.** Each session gets `.claude/settings.json` deny rules: no web, no `git clone`/`curl`, no access to the other arms, the hidden tests or the oracle. The sqlfluff arms get a history-free snapshot of the base commit, so the PR is not in `git log`.
- **Hidden tests.** In experiment 2 the acceptance tests are the three test files from the real PR. The same files are planted into every run: base, oracle (the merged PR) and each arm. Acceptance tests are those the oracle passes and the base fails. Regression tests are those both pass.
- **Sanity gate.** Before running any arm, I scored the base and the oracle. The oracle passed all 18 acceptance tests and failed none of the 3132 regression tests. The 104 excluded tests were all skips.
- **Pre-registered decision rule.** Arm B had to pass at least 40% of the tests arm A failed, break at most 2 more regression tests than A, and do so in 2 of 3 pairs. If arm A failed nothing, the task was declared non-discriminating.

## Experiment 1: pedantix gets JSON support

[pedantix](https://github.com/Swarsel/pedantix) is a roughly 4,000-line Rust CLI that sorts attributes in Nix files. The task asked it to sort JSON object keys with the same config. Scoring used 106 recorded black-box contracts for the existing Nix behaviour (98 discriminating after removing cases a do-nothing dummy also passes). It also used 40 hand-written JSON cases, 23 of them checking that the existing hidden rules carry over.

Both arms passed everything and converged on nearly the same design. Lesson: in a repo this small, a strong model reads all the relevant code in minutes. This is a ceiling effect, not a result.

## Experiment 2: sqlfluff PR #8580

[sqlfluff](https://github.com/sqlfluff/sqlfluff) is a widely used SQL linter with about 156k lines of Python. [PR #8580](https://github.com/sqlfluff/sqlfluff/pull/8580), merged on 3 October 2026, adds `list_wrapping = fill` to rule LT05. This makes long comma lists pack as many elements per line as fit, instead of one per line. The change sits in the core reflow engine (`reindent.py`, about 2,900 lines), so the whole repo cannot be read.

The map ([`examples/sqlfluff-blueprint/`](examples/sqlfluff-blueprint/)) took 20 minutes to extract and has 58 invariants and 314 verified pointers. It found real documentation errors, including a documented exit code the code never returns and three mistakes in the repo's own `AGENTS.md`. It also explicitly listed `reindent.py`'s algorithm as "not examined", which is where the task lives.

With Opus, both arms built nearly the same design as the PR author: same branch of `lint_line_length`, greedy fill, the `alone` comma's two break points kept together, and length measured on source text. With Haiku, all six runs got the hard parts right. Three of them misread one sentence of the task about `alone` commas.

## Why I stopped

Formally, the decision rule passed for Haiku (2 of 3 pairs). I don't count it as evidence:

- The whole difference is one test flipping in one of three runs.
- The map contains no information about that test.
- In one pair, the arm with the map was the one that failed it.

The rule itself was the problem: it had no minimum effect size, so a single test was enough to clear the 40% threshold.

The broader picture is a structural tension. The repos where a map would help (no tests, no docs, no agent guide) are the ones few people use. The widely used repos already have tests, docs and increasingly an `AGENTS.md`, and strong agents do fine on them.

## What I learned

1. **Search for prior work first.** Two studies already answered most of this question before I started. A one-hour literature search would have changed the experiment, or replaced it.
2. **Pre-register an effect size, not just a ratio.** "B passes 40% of A's failures" sounds strict, but it is trivially met when A fails a single test.
3. **Design for a baseline that fails.** Both experiments hit the ceiling. An experiment only measures something if the control arm has room to be wrong.
4. **Failures came from interpretation, not missing knowledge.** Every failed run had the information it needed in the task text and misread it. A map cannot fix that.
5. **Validate the harness before the arms.** Scoring the base and the oracle first proved the hidden tests were solvable and discriminating, so every later number could be trusted.

## How this was built

I ran this project with Claude (Opus 5.5) as a collaborator. Claude drafted most of the code, the task texts and this README. I chose the direction, picked the repos, ran every session on my own machine and made the go/stop calls. Given the subject, it seemed right to say so.

## Limitations

This is one person's small experiment, not a benchmark. It covers two repos, one real-PR task, and at most four runs per arm and model. The task text for sqlfluff was detailed, written from the PR's own docs. A vaguer, more realistic request might leave more room for a map. Effects smaller than one test per task cannot be detected at this sample size.

## Related work

- Gloaguen et al., *Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for Coding Agents?* (ICLR 2026, [arXiv:2602.11988](https://arxiv.org/abs/2602.11988)). They find that context files tend to lower task success compared with no context and raise inference cost by over 20%. Repository overviews in particular did not help agents find relevant files faster.
- Khatri, *Do Context Files Help Coding Agents? A Two-Agent Ablation Study on Real Repositories* (2026, [arXiv:2607.27250](https://arxiv.org/abs/2607.27250)). Context strategy did not measurably move correctness, and agents failed on implementation skill rather than missing repository knowledge.

## Repository layout

```
extract-skill/                the generic /extract skill (Claude Code) that writes a map
examples/sqlfluff-blueprint/  the map used in experiment 2 (map.yaml is the source, README.md is derived)
experiment-1-pedantix/        black-box contract runner, case generators, recorded expectations, task texts
experiment-2-sqlfluff/        setup script, hidden-test scorer, task texts for both arms
original-tr/                  the Turkish originals the agents actually saw
results/runs.csv              one row per run
```

I worked in Turkish, so the skill, the task texts and the maps the agents saw were written in Turkish. The files in this repo are English translations. The originals are kept unchanged in [`original-tr/`](original-tr/), and `TASK_LANG=tr bash experiment-2-sqlfluff/setup.sh` reproduces the runs with them. The sqlfluff `map.yaml` (1,282 lines) is kept in its original Turkish. Its human view, `examples/sqlfluff-blueprint/README.md`, is translated. The skill's "Large repos" section was added after experiment 1 and before experiment 2.

### Reproducing experiment 2

Requires macOS or Linux, git and a Claude Code login. `setup.sh` installs [uv](https://github.com/astral-sh/uv) if missing, clones sqlfluff, builds history-free snapshots of the base commit (`c01adec`) and the PR commit (`cc44abf`), extracts the hidden tests and creates one Python environment per session.

```bash
bash experiment-2-sqlfluff/setup.sh          # extract + pair 1
bash experiment-2-sqlfluff/setup.sh 2        # another pair
cd ~/Desktop/contracts/sqlfluff
score-venv/bin/python score.py run base snap/base
score-venv/bin/python score.py run oracle snap/oracle
score-venv/bin/python score.py run arm-a-1 ~/Desktop/blueprint-runs/sq/arm-a-1
score-venv/bin/python score.py report arm-a-1:arm-b-1
```

Paths are hard-coded to `~/Desktop`, as in my runs.

### Checking experiment 1

`experiment-1-pedantix/suites/*/expected/` holds the recorded expectations: the Nix contracts were recorded from pedantix commit `b8dbd3b`, and the JSON cases were written by hand. To score a build:

```bash
python3 experiment-1-pedantix/contract.py check --bin path/to/pedantix --suite experiment-1-pedantix/suites/pedantix
python3 experiment-1-pedantix/contract.py check --bin path/to/pedantix --suite experiment-1-pedantix/suites/pedantix-json
```

## Acknowledgements

Thanks to the sqlfluff maintainers and to Yash Raj Pandey, author of PR #8580, whose tests made a fair benchmark possible. Thanks also to Leon Schwarzäugl (Swarsel) for pedantix. Both projects are MIT licensed. The example map is derived from sqlfluff's source.
