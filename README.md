# Offline CSV Preflight

A small Python 3.9+ work sample that finds structural and required-field issues before a CSV is mapped or imported. It reads a file and prints JSON; it does not repair or overwrite source data, call a service, or execute cell content. No packages or credentials are needed.

## Run

Save the synthetic block below as `sample.csv`, preserving the quoted line break:

```csv
id,status,note
00017,open,first
00017,closed,conflict
00018,,missing status
00019,open,"two
lines"
00020,open,ok,EXTRA
,open,missing id
00021,open,ok
```

Then run:

```sh
python3 check_csv.py sample.csv --key id --require status
python3 -m unittest -v
```

The example reports **7 data records, 5 records with issues, and 4 issue entries**. Duplicate-key issues group every occurrence, so the number of issue entries differs from the number of affected records. `sample-report.json` contains the actual CLI output for this block. An exit code of **1 is expected** for this example because the input deliberately contains problems.

## Contract

- Input is comma-delimited UTF-8, with an optional BOM. Quoting uses Python's standard `csv.reader` in strict mode. This is not a claim of validating every CSV dialect or the entire RFC.
- Header names must be nonempty, unique and have no surrounding whitespace. Declared columns must exist. Extra, uniquely named columns are allowed.
- The key column is always required. Repeat `--require field_name` for other fields. Empty and whitespace-only values are missing; the string `0` is present.
- Keys are compared as exact strings. `001`, `1`, `A`, `a` and ` A ` are distinct. This tool does not infer case/whitespace normalization rules or whether identifiers refer to the same entity.
- Rows with a column-count mismatch are flagged and counted, including blank records. Their fields are not interpreted for missing-value or duplicate checks.
- Duplicate groups flag all matching nonblank keys among correctly sized rows. The tool does not decide whether an exact repeat or a conflicting duplicate should be kept, merged or deleted.
- `records` are logical CSV record numbers, with the header numbered 1. `line_ends` are physical ending line numbers, so quoted multiline fields do not make location references ambiguous.
- The report includes header names, declared rules, counts and locations, but does not echo cell values. Header names can themselves be sensitive; review a report before sharing it.

Exit status: **0** means no issues under these limited checks; **1** means a complete report with findings; **2** means unreadable/invalid UTF-8 input, invalid headers, a missing declared column, a CSV parse error or an argument error. Fatal errors have stderr output and no partial JSON report. A header-only file contains zero data records and passes these limited checks.

This checker does not validate dates, amounts, formulas, external identifiers, destination permissions or business rules. Its report is not a cleaned import file or a completed customer workflow. Source preservation applies to the program's own operations: when redirecting stdout, use a separate report path, never the input path.

## Evidence and authorship

The tests exercise real CLI calls, source-byte preservation, duplicate locations, blank versus zero, ragged records, BOMs, quoted commas/newlines, fatal input errors and repeatable output. Fixtures are synthetic. The behavior of Python's reader and its string values is documented in the [official CSV reference](https://docs.python.org/3/library/csv.html).

Tiee is an AI-assisted technical-services project. This is an independent demonstration, not a paid client case study. For a scoped file-preparation task, contact tieetheai@gmail.com with a redacted example and an expected result. Scope, acceptance and payment terms are agreed before work starts.
