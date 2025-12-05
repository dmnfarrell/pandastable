import unittest
import pandas as pd
import numpy as np
import os
import shutil
import tempfile
from pathlib import Path
from io import StringIO
import utils
import plotting_utils
import file_ops

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


class TestFileOps(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.src_dir = Path(self.tmpdir.name) / "src"
        self.dest_dir = Path(self.tmpdir.name) / "dest"
        self.src_dir.mkdir(parents=True, exist_ok=True)
        self.dest_dir.mkdir(parents=True, exist_ok=True)
        self.sample_path = self.src_dir / "sample_data.csv"
        self.sample_path.write_text("col\n1\n", encoding="utf-8")
        self.record = {
            "Name": "sample_data.csv",
            "Directory": str(self.src_dir),
            "Path": str(self.sample_path),
        }

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_copy_or_move_files_copy_success(self):
        kind, message, successes, mutated = file_ops.copy_or_move_files(
            [self.record],
            str(self.dest_dir),
            overwrite=False,
            operation='copy'
        )
        self.assertEqual(kind, "success")
        self.assertTrue((self.dest_dir / "sample_data.csv").exists())
        self.assertEqual(mutated, [])
        self.assertTrue(successes)

    def test_rename_files_updates_filename(self):
        kind, message, successes, mutated = file_ops.rename_files(
            [self.record],
            "{stem}_v2",
            overwrite=False
        )
        self.assertEqual(kind, "success")
        self.assertIn("sample_data.csv → sample_data_v2.csv", successes)
        self.assertTrue((self.src_dir / "sample_data_v2.csv").exists())
        self.assertIn(str(self.sample_path), mutated)

    def test_apply_rename_template_uses_parts(self):
        record = dict(self.record)
        record["Part 1"] = "LotA"
        new_name = file_ops.apply_rename_template(record, "{Part_1}_{stem}")
        self.assertEqual(new_name, "LotA_sample_data.csv")


class TestTouchstoneAndSpecialPlots(unittest.TestCase):
    def test_load_touchstone_parses_ports_and_matrix(self):
        content = """# Hz S RI R 50\n100 1 0 0 0 0 0 1 0\n"""
        data = plotting_utils.load_touchstone(StringIO(content))
        self.assertEqual(data['ports'], 2)
        self.assertEqual(data['matrix'].shape, (1, 2, 2))
        self.assertTrue(np.isclose(data['matrix'][0, 0, 0], 1 + 0j))
        labels = plotting_utils.get_sparameter_labels(data)
        self.assertEqual(labels, ['S11', 'S12', 'S21', 'S22'])

    def test_plot_s_parameters_returns_figure(self):
        content = """# GHz S RI R 50\n1 1 0 0 0 0 0 1 0\n"""
        data = plotting_utils.load_touchstone(StringIO(content))
        fig = plotting_utils.plot_s_parameters(data, [(1, 1)], display_mode='mag_db', log_freq=True)
        self.assertIsNotNone(fig)
        self.assertEqual(fig.axes[0].get_xscale(), 'log')

    def test_plot_jitter_produces_histogram(self):
        df = pd.DataFrame({'jitter': np.linspace(-0.1, 0.1, 50)})
        fig = plotting_utils.plot_jitter(df, 'jitter', bins=20, show_gaussian=True, show_stats=True)
        self.assertEqual(fig.axes[0].get_title(), 'Jitter Histogram')

    def test_plot_phase_noise_requires_numeric_columns(self):
        df = pd.DataFrame({
            'offset': np.logspace(3, 6, 10),
            'noise': np.linspace(-90, -110, 10)
        })
        fig = plotting_utils.plot_phase_noise(df, 'offset', 'noise', carrier_hz=2e9)
        self.assertEqual(fig.axes[0].get_xscale(), 'log')

if __name__ == '__main__':
    unittest.main()
