import csv
import json
import tempfile
import unittest
from pathlib import Path
from bdphenology.reference import ANNUAL_FIELDS, check_reference, make_package, spatial_split


class ReferenceTests(unittest.TestCase):
    def write(self,path,rows,fields=ANNUAL_FIELDS):
        with path.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

    def reviewed(self):
        return {'sample_id':'s1','year':'2025','reference_land_cover':'cropland',
                'annual_review_complete':'yes','reference_cycle_count':'2',
                'source_type':'field_record','source_reference':'synthetic-test-record',
                'source_dates':'2025-01-01 to 2025-12-31','reviewer':'test',
                'review_date':'2026-10-16'}

    def test_blank_labels_are_not_zero_cycles(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'reference.csv'
            self.write(p,[{'sample_id':'s1','year':'2025'}])
            r=check_reference(p)
            self.assertEqual(r['status_counts'],{'unreviewed':1})
            self.assertIsNone(r['accuracy'])

    def test_missing_source_cannot_be_ready(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'reference.csv';r=self.reviewed();r['source_reference']=''
            self.write(p,[r]);out=check_reference(p)
            self.assertEqual(out['status_counts'],{'invalid':1})
            self.assertIn('missing_source_reference',out['errors'][0]['issues'])

    def test_incomplete_review_cannot_claim_a_count(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'reference.csv';r=self.reviewed();r['annual_review_complete']='no'
            self.write(p,[r]);out=check_reference(p)
            self.assertIn('incomplete_review_requires_blank_count',out['errors'][0]['issues'])

    def test_complete_review_still_does_not_produce_model_accuracy(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'reference.csv';self.write(p,[self.reviewed()])
            out=check_reference(p)
            self.assertEqual(out['ready_sample_ids'],['s1'])
            self.assertIsNone(out['accuracy'])

    def test_spatial_block_assignment_is_shared_and_reproducible(self):
        self.assertEqual(spatial_split(90.011,22.011),spatial_split(90.019,22.019))

    def test_package_is_blind_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder);source=folder/'input.csv'
            self.write(source,[{'sample_id':'s1','longitude':'90.1','latitude':'22.1','district':'Barguna'}],
                       ['sample_id','longitude','latitude','district'])
            out=folder/'out';manifest=make_package(source,out)
            self.assertEqual(manifest['reference_labels_entered'],0)
            with (out/'annual_reference.csv').open() as f:rows=list(csv.DictReader(f))
            self.assertEqual(rows[0]['reference_cycle_count'],'')
            self.assertNotIn('candidate_event_count',rows[0])
            self.assertEqual(json.loads((out/'sample_locations.geojson').read_text())['features'][0]['geometry']['coordinates'],[90.1,22.1])
            with self.assertRaisesRegex(ValueError,'protect existing'):make_package(source,out)
