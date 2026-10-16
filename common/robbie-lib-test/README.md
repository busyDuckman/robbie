# robbie-lib-test

Shared test data for robbie-lib-py and robbie-lib-rs. Both libraries run the same cases, which proves the port behaves the same.

## relm/

  - `example_table.yaml`  the RELM to IRELM table the convert cases use by default.
  - `convert_cases.json`  RELM in, IRELM out (or an error kind), with the relm CLI options.
  - `table_cases.json`    tables that must load, or fail with bad_table.
  - `say_as_cases.json`   AS expansion: format, locale and text in, words out.

The tests compare error kinds, not messages.
