"""Read-only CSV diagnostics; no repair, type coercion, or network operations."""

import argparse
import csv
import io
import json
import sys


def inspect_csv(text, key, required=()):
    reader = csv.reader(io.StringIO(text.lstrip('\ufeff'), newline=''), strict=True)
    try:
        header = next(reader, None)
        if (not header or any(not name or name != name.strip() for name in header)
                or len(set(header)) != len(header)):
            raise ValueError('invalid header: names must be unique, nonempty and unpadded')
        required = list(dict.fromkeys([key, *required]))
        if any(name not in header for name in required):
            raise ValueError('a declared key/required column is absent from the header')
        indexes = {name: header.index(name) for name in required}
        issues, groups, affected = [], {}, set()
        rows_seen = 0
        for record, row in enumerate(reader, start=2):
            rows_seen += 1
            location = {'records': [record], 'line_ends': [reader.line_num]}
            if len(row) != len(header):
                issues.append({'code': 'column_count', 'expected': len(header),
                               'actual': len(row), **location})
                affected.add(record)
                continue
            for field, index in indexes.items():
                if not row[index].strip():
                    issues.append({'code': 'missing_value', 'field': field, **location})
                    affected.add(record)
            value = row[indexes[key]]
            if value.strip():
                groups.setdefault(value, []).append((record, reader.line_num))
        for locations in groups.values():
            if len(locations) > 1:
                records, line_ends = zip(*locations)
                issues.append({'code': 'duplicate_key', 'field': key,
                               'records': list(records), 'line_ends': list(line_ends)})
                affected.update(records)
        return {'header': header, 'key_column': key, 'required_columns': required,
                'rows_seen': rows_seen, 'rows_with_issues': len(affected),
                'issue_count': len(issues), 'issues': issues}
    except csv.Error as error:
        raise ValueError('invalid CSV syntax near physical line %s' % reader.line_num) from error


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input')
    parser.add_argument('--key', required=True, help='exact unique identifier column')
    parser.add_argument('--require', action='append', default=[], help='nonblank column; repeatable')
    args = parser.parse_args(argv)
    try:
        with open(args.input, encoding='utf-8-sig', newline='') as source:
            report = inspect_csv(source.read(), args.key, args.require)
    except UnicodeError:
        print('error: cannot decode input as UTF-8', file=sys.stderr)
        return 2
    except OSError:
        print('error: cannot read input file', file=sys.stderr)
        return 2
    except ValueError as error:
        print('error: ' + str(error), file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report['issues'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
