# Task

This folder is a copy of the repo of the SQL linter `sqlfluff`. The user's request is:

> When LT05 splits a long comma separated list (for example the terms of a `GROUP BY`, or the arguments of a function), it currently puts each element on its own line. I'd like an option that instead puts as many elements on each line as fit.
>
> Add a setting called `list_wrapping` to the `[sqlfluff:indentation]` section of the config:
>
> ```ini
> [sqlfluff:indentation]
> list_wrapping = fill
> ```
>
> Its values should be `one_per_line` and `fill`. The default should be `one_per_line`, and today's behaviour must not change at all.
>
> Example: with `max_line_length = 45`, today's output is:
>
> ```sql
> SELECT a
> FROM tbl
> GROUP BY
>     long_column_name1,
>     long_column_name2,
>     long_column_name3,
>     long_column_name4
> ```
>
> With `list_wrapping = fill` it should be:
>
> ```sql
> SELECT a
> FROM tbl
> GROUP BY
>     long_column_name1, long_column_name2,
>     long_column_name3, long_column_name4
> ```

The `blueprint/` folder at the repo root is an adaptation map of this code base. Read `blueprint/README.md` first, and `blueprint/map.yaml` for details, then start working.

## Details

1. Put as many elements on each line as fit without exceeding the limit. Measure line length the way LT05 measures it today: including the indent, and for templated (Jinja) SQL by the source text, not the rendered text.
2. Fill only splits a line that is too long. It does not join lines, and it keeps line breaks that already exist in a list. It does not touch a line within the limit.
3. The configured comma position (`trailing`, `leading`, `alone`) still applies where a line is split. With `alone`, the comma still sits on its own line.
4. Only comma separated lists are filled. Operators such as `AND`, `OR` and `+` are not filled; as today, each gets its own line break.
5. In nested lists, LT05's current order is kept: the outer list is split first, then the inner list if needed.
6. LT05 does not split inside a template tag (`{{ ... }}`, `{% ... %}`). If a single tag renders the whole list, the line stays too long with either setting.
7. LT09 always puts multiple select targets on separate lines. That must not change. If LT09 is turned off with `exclude_rules`, select targets are filled too.
8. When `sqlfluff fix` is run twice, the second run must change nothing.
9. An invalid value (including upper-case spellings like `FILL`, an empty string or a number) must raise `SQLFluffUserError` during config validation. The message must follow the pattern of the existing `implicit_indents` validation message: ``... set an invalid value for `list_wrapping`: <repr of the value>. Valid options are: one_per_line, fill. ...``
10. The new setting, with its default value, must appear in the default config file.

## Working rules

1. Make your changes in this folder.
2. Do not go online. Do not download, install or inspect any other version of sqlfluff.
3. Do not read files outside this folder.
4. Do not ask questions; nobody will answer in this session. If something is ambiguous, choose the most reasonable interpretation and write it in `NOTES.md`.
5. The Python environment is ready: run tests with `.venv/bin/python -m pytest ...`. The whole test suite takes a long time; pick the relevant tests.
6. Updating the documentation is optional.

## When you finish

- Add your own tests for the new behaviour.
- The existing tests in the areas your change touches must pass.
- Write `NOTES.md` at the repo root with:
  1. The files you changed and added.
  2. The points you found ambiguous and the interpretation you chose for each.
  3. Anything you are unsure of or could not finish.
  4. Which tests you ran and their results.
  5. Roughly how many steps and how long it took you.

If you hit the usage limit, write in `NOTES.md` where you stopped before you stop.
