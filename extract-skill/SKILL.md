---
name: extract
description: Extracts a blueprint from a code base, i.e. a code-verified adaptation map. Use when the user types /extract or asks for a blueprint of a repo.
---

# Blueprint extraction

## Goal

Produce a **code-verified adaptation map** for an agent and a human who will want to adapt this repo to their own needs. The map should answer:

- Which parts of the code are the **portable core** (logic not tied to a particular domain), and which are the **domain layer** (tied to a particular file format, language, protocol, platform or external tool)?
- Where and through which interface do the two connect?
- What has to be touched to add a new variant?
- Where does the code assume things about the domain?
- What **must not break**? Especially behaviour the documentation does not mention.

**You do not know which adaptation will be made.** The map must serve every kind of adaptation equally well: a new input type, a new platform, a new command, replacing a component or porting to another language. Do not assume a particular adaptation, do not emphasise one, and do not write a ready-made solution for one.

## Output

A `blueprint/` folder at the repo root. See `FORMAT.md` in this folder for the detailed schema.

- `blueprint.yaml`: identity (repo, commit, date, size, extracting model).
- `map.yaml`: **the single source of truth.** The structured map agents read.
- `README.md`: the human view. Derived only from `map.yaml`; adds no new claims.

## Steps

1. **Inventory.** Before reading, gather with commands: `git rev-parse HEAD`, the file tree, languages and line counts, dependency files, entry points, test folders, documentation files.
2. **Read the documentation** (README, docs/, example config files). Note concrete claims: key names, defaults, value lists, descriptions of behaviour. You will compare them with the code later.
3. **Trace the code from the entry point.** List, in order, the stages an input passes through.
4. **Module map.** For each module, give its role and layer: `core`, `domain` or `mixed`. For `mixed` modules, also give the domain-specific line ranges.
5. **Seams.** Find the interfaces between the core and the domain layer. If there is no explicit interface and domain knowledge is embedded in the core, mark it `embedded` and list where it is embedded.
6. **Extension points.** Describe the code's current mechanism for adding a new kind of variant (input type, command, backend, output target; whichever make sense for the repo). For example: selection by file extension, an enum, a trait/interface, a registry. Give every place that has to be touched as a checklist. Do this separately for each kind of variant that makes sense for the repo.
7. **Embedded assumptions.** Look for domain-specific constants and checks: file extensions, hard-coded tool names, parser node types, hard-coded paths, special file names. Write each with `file:line` and what it affects.
8. **Invariants.** Extract user-observable behaviour that must not break. **Prioritise what the documentation does not say.** Scan these categories one by one:
   - sorting and comparison semantics (case, numbers, Unicode, ties),
   - config discovery, layering and precedence,
   - CLI exit codes, stdout vs. stderr, when files are written,
   - error cases and their scope (one file, or the whole run),
   - safety checks, warnings, idempotency, defaults,
   - how settings affect each other (does one setting disable another?).

   For each invariant write: the statement, evidence (`file:line`), the repo test that covers it if any, a confidence level, and whether it is documented. If possible, build the tool and observe the behaviour by running it on small inputs; an invariant you observed gets confidence `verified`.
9. **Documentation discrepancies.** Compare each concrete claim noted in step 2 with its definition in the code. Write down those that contradict the code and those with no counterpart in the code.
10. **Unknowns.** Write behaviour you could not be sure of, despite reading the code, as questions.
11. **Write.** Write `map.yaml` first, then derive `README.md` from it.
12. **Check.**
    - Reopen every `file:line` pointer and verify it really shows what is claimed.
    - Every claim in the README must have a counterpart in `map.yaml`.
    - The blueprint's total size must not exceed roughly 10% of the code.

## Large repos

If the source code exceeds roughly 20,000 lines, this section changes how steps 1–12 are applied.

- **Size limit.** Instead of the 10% rule, apply a readability limit: `README.md` at most about 400 lines, `map.yaml` at most about 2,500 lines.
- **Repeating families.** If many members are written to the same pattern (languages, plugins, rules, adapters, drivers and the like), do not map each member separately. Write the family as one pattern: the shared interface, the list or location of members, a representative member, a checklist for adding a member, and the members that deviate from the pattern.
- **Depth goes to the core.** Spend the space you save on the core machinery shared by many families or features. For long, complex core modules, produce an internal map: the main functions, the calls and data flow between them, which decision is made in which function, and the points a change that adds behaviour to this module would have to touch.
- **Existing agent and contribution docs.** Read files like `AGENTS.md`, `CLAUDE.md` and `CONTRIBUTING`. Do not repeat what they say; point to them. Devote the map to what these files do not say, and record contradictions in step 9.
- **Tests.** Do not run the whole test suite. To verify an invariant, run only the relevant tests or the tool itself on small inputs.
- **Prioritisation.** If you cannot cover everything to the same depth, list the areas you did not cover in `unknowns` as "not examined".

## Rules

- Do not touch the repo's code. Write only to the `blueprint/` folder.
- Do not go online. Use only the information in the repo.
- Do not invent. Put anything you are unsure of in `unknowns`. Mark guesses `confidence: guess`.
- Answer "why is it like this?" only with evidence: a code comment, a commit message or a test name. If there is no evidence, do not write a reason.
- Write briefly and concretely. Each item should say one thing.
