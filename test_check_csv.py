import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('check_csv.py')


class CsvPreflightTests(unittest.TestCase):
    def run_check(self, data, *options):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'input.csv'
            source.write_bytes(data)
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(source), '--key', 'id',
                 '--require', 'status', *options], capture_output=True, text=True)
            self.assertEqual(source.read_bytes(), data)
            return result

    def test_clean_bom_quoted_fields_and_distinct_leading_zero_keys(self):
        result = self.run_check(b'\xef\xbb\xbfid,status,note\r\n001,open,"a,b"\r\n1,closed,0\r\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['rows_seen'], 2)
        self.assertEqual(report['rows_with_issues'], 0)
        self.assertEqual(report['issues'], [])

    def test_duplicates_include_first_occurrence_without_echoing_cell_values(self):
        result = self.run_check(b'id,status\nprivate-id,open\nprivate-id,closed\n')
        self.assertEqual(result.returncode, 1, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['rows_with_issues'], 2)
        self.assertEqual(report['issues'], [
            {'code': 'duplicate_key', 'field': 'id', 'records': [2, 3], 'line_ends': [2, 3]}])
        self.assertNotIn('private-id', result.stdout)

    def test_ragged_blank_and_missing_records_stay_visible(self):
        result = self.run_check(b'id,status\nA,\nB,open,extra\n,open\n\n')
        self.assertEqual(result.returncode, 1, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual((report['rows_seen'], report['rows_with_issues']), (4, 4))
        self.assertEqual([x['code'] for x in report['issues']],
                         ['missing_value', 'column_count', 'missing_value', 'column_count'])
        self.assertEqual([x['records'] for x in report['issues']], [[2], [3], [4], [5]])

    def test_structural_errors_do_not_produce_a_partial_report(self):
        for data, message in [
            (b'', 'header'), (b'id,id\na,b\n', 'header'),
            (b'id, status\na,b\n', 'header'), (b'id,\na,b\n', 'header'),
            (b'id,note\na,b\n', 'column'),
            (b'id,status\na,"unfinished\n', 'CSV'),
            (b'id,status\na,\xff\n', 'decode'),
        ]:
            with self.subTest(data=data):
                result = self.run_check(data)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, '')
                self.assertIn(message, result.stderr)

    def test_multiline_locations_and_repeated_runs(self):
        data = b'id,status,note\na,open,"two\nlines"\na,closed,x\n'
        first = self.run_check(data)
        self.assertEqual(first.returncode, 1, first.stderr)
        issue = json.loads(first.stdout)['issues'][0]
        self.assertEqual(issue['records'], [2, 3])
        self.assertEqual(issue['line_ends'], [3, 4])
        self.assertEqual(first.stdout, self.run_check(data).stdout)

    def test_whitespace_only_required_value_is_missing_but_zero_is_present(self):
        result = self.run_check(b'id,status\na, \nb,0\n')
        self.assertEqual(result.returncode, 1, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['rows_with_issues'], 1)
        self.assertEqual(report['issues'][0]['records'], [2])


if __name__ == '__main__':
    unittest.main()
