import math
import unittest
from datetime import date, timedelta
from bdphenology.cycles import detect


class CycleTests(unittest.TestCase):
    def series(self):
        start = date(2023, 7, 1)
        return [(start + timedelta(days=15*i),
                 0.15 + 0.65 * max(0, math.sin(2*math.pi*((start+timedelta(days=15*i)-date(2024, 1, 1)).days)/120)))
                for i in range(49)]

    def test_three_complete_growth_episodes(self):
        result = detect(self.series(), 2024)
        self.assertEqual(result['count'], 3)
        self.assertTrue(all(c['duration_days'] >= 40 for c in result['cycles']))

    def test_missing_observation_prevents_confident_annual_count(self):
        points = self.series()
        points[20] = (points[20][0], None)
        self.assertIsNone(detect(points, 2024)['count'])

    def test_partial_year_prevents_confident_annual_count(self):
        points = [(d,v) for d,v in self.series() if date(2024, 4, 1) <= d <= date(2024, 9, 1)]
        self.assertIsNone(detect(points, 2024)['count'])

    def test_no_seasonal_signal(self):
        self.assertEqual(detect([(d, 0.15) for d,v in self.series()], 2024)['count'], 0)

    def test_duplicates_rejected(self):
        with self.assertRaises(ValueError):
            detect(self.series() + self.series()[:1], 2024)

    def test_absent_target_year(self):
        self.assertIsNone(detect(self.series(), 2020)['count'])


if __name__ == '__main__':
    unittest.main()
