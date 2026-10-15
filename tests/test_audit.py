import csv
import tempfile
import unittest
from pathlib import Path
from bdphenology.audit import audit


class AuditTests(unittest.TestCase):
    def test_source_errors_are_flagged_without_repair(self):
        fields = ['District', 'Crop Name', 'Season', 'Area', 'Production', 'AP Ratio',
                  'Max Relative Humidity', 'Min Relative Humidity']
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'source.csv'
            with path.open('w', newline='') as handle:
                writer = csv.writer(handle)
                writer.writerow(fields)
                writer.writerow(['Chattogram', 'Aman', 'Kharif 2', 10, 20, 2, 60, 85])
                writer.writerow(['Noakhali', '#REF!', 'Kharif 1', 0, 0, '#DIV/0!', 60, 85])
            original = path.read_bytes()
            result = audit(path)
            self.assertEqual(result['humidity_max_below_min_rows'], 2)
            self.assertEqual(result['zero_area_rows'], 1)
            self.assertEqual(result['ratio_matches_production_divided_by_area'], 1)
            self.assertEqual(result['spreadsheet_errors']['AP Ratio: #DIV/0!'], 1)
            self.assertFalse(result['year_column_present'])
            self.assertEqual(path.read_bytes(), original)

    def test_unrelated_schema_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'other.csv'
            path.write_text('city,value\nChattogram,1\n')
            with self.assertRaisesRegex(ValueError, 'Missing required columns'):
                audit(path)
