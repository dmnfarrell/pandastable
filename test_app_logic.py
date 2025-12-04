import unittest
import pandas as pd
import numpy as np
import os
import shutil
import utils
import plotting_utils

class TestAppLogic(unittest.TestCase):
    def setUp(self):
        # Create a dummy CSV file
        self.csv_path = 'test_data.csv'
        self.df = pd.DataFrame({
            'A': [1, 2, 3, 4, 5],
            'B': [10, 20, 30, 40, 50],
            'C': ['foo', 'bar', 'baz', 'foo', 'bar'],
            'D': [1.1, 2.2, 3.3, 4.4, 5.5]
        })
        self.df.to_csv(self.csv_path, index=False)

    def tearDown(self):
        if os.path.exists(self.csv_path):
            os.remove(self.csv_path)

    def test_load_csv(self):
        df = utils.load_csv_file(self.csv_path)
        self.assertEqual(len(df), 5)
        self.assertListEqual(list(df.columns), ['A', 'B', 'C', 'D'])

    def test_row_filter_query(self):
        df = utils.apply_row_filter(self.df, "A > 3")
        self.assertEqual(len(df), 2)
        self.assertTrue(all(df['A'] > 3))

    def test_row_filter_contains(self):
        df = utils.apply_row_filter(self.df, "foo")
        self.assertEqual(len(df), 2)
        self.assertTrue(all(df['C'] == 'foo'))

    def test_row_filter_mixed(self):
        # query @ contains
        df = utils.apply_row_filter(self.df, "A > 1 @ foo")
        # A>1: 2,3,4,5. foo: 1,4. Intersection: 4.
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]['A'], 4)

    def test_column_filter(self):
        df = utils.apply_column_filter(self.df, "A, C")
        self.assertListEqual(list(df.columns), ['A', 'C'])

    def test_column_filter_wildcard(self):
        df = utils.apply_column_filter(self.df, "A, *")
        self.assertListEqual(list(df.columns), ['A', 'B', 'C', 'D'])

    def test_column_filter_exclude(self):
        df = utils.apply_column_filter(self.df, "!B")
        self.assertListEqual(list(df.columns), ['A', 'C', 'D'])

    def test_numeric_varying_columns(self):
        cols = plotting_utils.get_numeric_varying_columns(self.df)
        self.assertIn('A', cols)
        self.assertIn('B', cols)
        self.assertIn('D', cols)
        self.assertNotIn('C', cols)

    def test_correlation(self):
        # Perfect correlation between A and B
        corr_df, _ = plotting_utils.get_top_correlated_columns(self.df, 'A')
        self.assertIsNotNone(corr_df)
        self.assertEqual(corr_df.iloc[0]['Column'], 'B')
        self.assertAlmostEqual(corr_df.iloc[0]['Correlation'], 1.0)

if __name__ == '__main__':
    unittest.main()
