import csv
import math
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from bdphenology.radar import radar_events, compare_sample, load_export, write_analysis


class RadarTests(unittest.TestCase):
    def rows(self, shift=0):
        start = date(2024,7,1)
        rows = []
        for i in range(49):
            day = start+timedelta(days=15*i)
            phase = 2*math.pi*(day-date(2025,1,1)).days/120
            vh = -20+4*math.sin(phase+shift)
            rows.append({'date':day,'ndvi':.4+.3*math.sin(phase),
                         'vv_db':vh+6,'vh_db':vh,'valid_pixels':1,
                         'district':'Synthetic','sample_id':'synthetic'})
        return rows

    def test_sustained_radar_patterns_detected(self):
        events = radar_events(self.rows(), 2025)
        self.assertEqual(len(events), 3)
        self.assertTrue(all(e['rise_db'] >= 3 and e['fall_db'] >= 3 for e in events))

    def test_flat_radar_does_not_generate_events(self):
        rows = self.rows()
        for r in rows:r['vh_db'] = -17
        self.assertEqual(radar_events(rows, 2025), [])

    def test_isolated_spike_suppressed(self):
        rows = self.rows()
        for r in rows:r['vh_db'] = -20
        rows[20]['vh_db'] = -9
        self.assertEqual(radar_events(rows, 2025), [])

    def test_long_radar_gap_not_bridged(self):
        rows = self.rows()
        for r in rows:
            if date(2025,1,1) <= r['date'] <= date(2025,4,1):r['vh_db'] = None
        events = radar_events(rows, 2025)
        self.assertFalse(any(e['peak_date'] < '2025-04-01' for e in events))

    def test_no_optical_data_stays_radar_only_and_unvalidated(self):
        rows = self.rows()
        for r in rows:r['ndvi'] = None
        result = compare_sample(rows, 2025)
        self.assertEqual(result['radar_event_count'], 3)
        self.assertEqual(result['matched_event_count'], 0)
        self.assertIsNone(result['annual_crop_cycle_count'])
        self.assertTrue(all('no_optical_observation_within_30_days_of_peak' in e['flags'] for e in result['events']))

    def test_matching_never_duplicates_an_optical_episode(self):
        result = compare_sample(self.rows(), 2025)
        self.assertGreater(result['matched_event_count'], 0)
        self.assertEqual(result['candidate_event_count'], result['radar_event_count']+
                         result['optical_episode_count']-result['matched_event_count'])

    def test_zero_prominence_rejected(self):
        with self.assertRaises(ValueError):radar_events(self.rows(),2025,prominence_db=0)

    def test_cli_outputs_are_reproducible_and_source_is_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'input.csv'
            with source.open('w',newline='') as f:
                w=csv.writer(f);w.writerow(['sample_id','date','ndvi','valid_pixels','vv_db','vh_db'])
                for r in self.rows():w.writerow(['synthetic',r['date'],r['ndvi'],1,r['vv_db'],r['vh_db']])
            original=source.read_bytes()
            summary=write_analysis(source,Path(directory)/'out',2025)
            self.assertEqual(summary['samples'],1)
            self.assertEqual(summary['validated_annual_crop_counts'],0)
            self.assertEqual(source.read_bytes(),original)
            self.assertEqual(summary,write_analysis(source,Path(directory)/'again',2025))
            with source.open('a') as f:f.write('synthetic,2025-01-01,0.3,1,-10,-16\n')
            # Deliberately append an actual existing date to test duplicate rejection.
            with source.open('a') as f:f.write(f"synthetic,{self.rows()[0]['date']},0.3,1,-10,-16\n")
            with self.assertRaisesRegex(ValueError,'Duplicate'):load_export(source)
