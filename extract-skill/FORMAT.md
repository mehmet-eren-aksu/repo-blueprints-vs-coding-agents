# Blueprint format (v0.2)

Keys are in English. In the original runs, descriptions were written in Turkish. All paths are relative to the repo root. Location pointers have the form `file:line` or `file:start-end`.

## blueprint.yaml

```yaml
format: blueprint/0.2
repo: <owner/name or folder name>
commit: <git rev-parse HEAD>
extracted_at: <YYYY-MM-DD>
extracted_by: <model name>
code_lines: <source lines excluding tests>
languages: {<language>: <lines>}
```

## map.yaml

```yaml
summary: <one sentence on what the tool does>

entrypoints:
  - where: <file:line>
    what: <what it starts>

pipeline:                 # the stages an input passes through, in order
  - id: P1
    stage: <short name>
    what: <what it does>
    where: [<file:line>]

modules:
  - path: <file or folder>
    role: <one sentence>
    layer: core | domain | mixed
    domain_lines: [<file:start-end>]   # only if mixed
    depends_on: [<path>]

seams:                    # connections between the core and the domain layer
  - id: S1
    name: <short name>
    kind: explicit | embedded
    interface: <function, trait or data structure signature>   # if explicit
    where: [<file:line>]
    note: <if embedded, how domain knowledge leaks into the core>

extension_points:         # today's way of adding a new variant
  - id: E1
    variant: <e.g. new input type, new command, new backend>
    mechanism: <how the code selects variants today>
    touch:                # every place that has to be touched
      - where: <file:line>
        what: <what must change>
    related_invariants: [<INV id>]
    tests: [<related test file or test name>]

assumptions:              # the code's assumptions about the domain
  - id: A1
    assumes: <what is assumed>
    where: [<file:line>]
    affects: <what it affects>

invariants:               # behaviour that must not break
  - id: INV-01
    category: sorting | config | cli | errors | safety | warnings | defaults | interaction | other
    statement: <one sentence, observable behaviour>
    evidence: [<file:line>]
    test: <test file::test name> | null
    confidence: verified | read | guess
    documented: yes | no | contradicts

config:
  sources: [<where config is read from, in precedence order>]
  discovery: <how the config file is found>
  precedence: <how the layers override each other>
  keys:
    - key: <key>
      type: <type>
      default: <default>
      applies_to: <what it applies to>
      where: <file:line>

cli:
  flags:
    - flag: <--flag>
      what: <what it does>
      where: <file:line>
  exit_codes: {<code>: <meaning>}
  io: <stdin, stdout, stderr and file-writing behaviour>

doc_discrepancies:
  - doc: <file:line>
    says: <what the documentation says>
    code: <file:line>
    actually: <what the code does>

unknowns:
  - question: <behaviour that could not be confirmed>
    where: [<file:line>]
```

## README.md (the human view)

Derived from `map.yaml`; adds no new claims. Each item carries its map id in parentheses (`INV-03`, `E1` and so on).

1. **One sentence:** `summary`.
2. **On one page:** what it does, a Mermaid diagram of the stages, a core/domain table and the 5 most important invariants.
3. **Adaptation guide:** a short checklist for each extension point, with the related invariants.
4. **Module details:** a few lines per module.
5. **Documentation discrepancies** and **unknowns.**
