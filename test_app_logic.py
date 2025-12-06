import unittest
from unittest import mock
import pandas as pd
import numpy as np
import os
import shutil
import tempfile
from pathlib import Path
from io import StringIO
import matplotlib.pyplot as plt
import utils
import plotting_utils
import file_ops
import app  # type: ignore
import streamlit as st

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

    def test_apply_column_text_filter_supports_include_exclude(self):
        df = app._apply_column_text_filter(self.df, 'Name', 'data')
        self.assertTrue(isinstance(df, pd.DataFrame))
        filtered = pd.DataFrame({'Name': ['test_data.csv', 'prod_results.csv', 'notes.txt']})
        result = app._apply_column_text_filter(filtered, 'Name', 'test !notes')
        self.assertEqual(result.iloc[0]['Name'], 'test_data.csv')
        self.assertNotIn('notes.txt', result['Name'].values)

    def test_apply_file_filters_handles_extension_and_size(self):
        sample = pd.DataFrame([
            {
                'Name': 'big.csv',
                'Directory': '/tmp',
                'Path': '/tmp/big.csv',
                'Extension': '.csv',
                'SizeBytes': 10_000,
                'ModifiedDt': pd.Timestamp('2024-01-01'),
            },
            {
                'Name': 'small.tsv',
                'Directory': '/tmp',
                'Path': '/tmp/small.tsv',
                'Extension': '.tsv',
                'SizeBytes': 100,
                'ModifiedDt': pd.Timestamp('2024-01-02'),
            },
        ])
        st_state = st.session_state  # type: ignore
        st_state.file_filter = ''
        st_state.file_name_filter = ''
        st_state.file_directory_filter = ''
        st_state.file_extension_filter = ['.csv']
        st_state.file_min_size_kb = 5
        st_state.file_max_size_kb = 0
        st_state.file_modified_after = ''
        st_state.file_modified_before = ''
        filtered = app._apply_file_filters(sample)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered.iloc[0]['Name'], 'big.csv')

    def test_display_plot_prefers_plotly_chart(self):
        fig = plt.figure()
        with mock.patch('app.mpl_to_plotly') as mock_convert, \
                mock.patch('app.st.plotly_chart') as mock_plotly, \
                mock.patch('app.st.pyplot') as mock_pyplot:
            mock_convert.return_value = 'plotly_fig'
            app._display_plot(fig)
            mock_convert.assert_called_once()
            mock_plotly.assert_called_once_with('plotly_fig', use_container_width=True)
            mock_pyplot.assert_not_called()

    def test_display_plot_falls_back_to_pyplot_on_error(self):
        fig = plt.figure()
        with mock.patch('app.mpl_to_plotly', side_effect=RuntimeError('boom')) as mock_convert, \
                mock.patch('app.st.plotly_chart') as mock_plotly, \
                mock.patch('app.st.pyplot') as mock_pyplot:
            app._display_plot(fig)
            mock_convert.assert_called_once()
            mock_plotly.assert_not_called()
            mock_pyplot.assert_called_once_with(fig)


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


class TestCorrelationPlots(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({
            'target': [1, 2, 3, 4, 5, 6],
            'B': [2, 4, 6, 8, 10, 12],
            'C': [10, 9, 8, 7, 6, 5],
            'group': ['g1', 'g1', 'g1', 'g2', 'g2', 'g2'],
        })

    def test_plot_correlation_grid_overlay(self):
        corr_df, _ = plotting_utils.get_top_correlated_columns(self.df, 'target', top_n=2)
        columns = [corr_df.iloc[0]['Column']]
        fig = plotting_utils.plot_correlation_grid(
            self.df,
            'target',
            corr_df,
            columns=columns,
            columns_per_row=1,
            show_regression=True,
            show_stats=True,
        )
        self.assertIsNotNone(fig)
        self.assertGreaterEqual(len(fig.axes), 1)
        self.assertIn(columns[0], fig.axes[0].get_title())
        plt.close(fig)

    def test_plot_correlation_grid_grouped_subplots(self):
        corr_df, _ = plotting_utils.get_top_correlated_columns(self.df, 'target', top_n=2)
        columns = corr_df['Column'].tolist()
        fig = plotting_utils.plot_correlation_grid(
            self.df,
            'target',
            corr_df,
            columns=columns,
            columns_per_row=2,
            group_col='group',
            subplots=True,
            sharex=True,
            sharey=True,
        )
        self.assertIsNotNone(fig)
        self.assertGreaterEqual(len(fig.axes), len(columns) * 2)
        plt.close(fig)

    def test_export_helpers_return_bytes(self):
        corr_df, _ = plotting_utils.get_top_correlated_columns(self.df, 'target', top_n=1)
        column = corr_df.iloc[0]['Column']
        csv_bytes = plotting_utils.export_correlations_csv(self.df, 'target', corr_df, [column])
        self.assertIsInstance(csv_bytes, bytes)
        self.assertIn(b'target', csv_bytes)
        fig = plotting_utils.plot_correlation_grid(
            self.df,
            'target',
            corr_df,
            columns=[column],
        )
        img_bytes = plotting_utils.export_correlation_figure(fig)
        self.assertIsInstance(img_bytes, bytes)
        self.assertGreater(len(img_bytes), 0)
        plt.close(fig)


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

    def test_compute_tdr_trace_generates_impedance_profile(self):
        content = """# GHz S RI R 50\n1 1 0 0 0 0 0 1 0\n2 0.9 0 0 0 0 0 0.9 0\n3 0.8 0 0 0 0 0 0.8 0\n"""
        data = plotting_utils.load_touchstone(StringIO(content))
        tdr = plotting_utils.compute_tdr_trace(
            data,
            parameter=(1, 1),
            mode='single_ended',
            velocity=0.6,
            points=256,
            window='none',
        )
        self.assertIn('impedance', tdr)
        self.assertEqual(len(tdr['impedance']), 256)
        self.assertGreater(np.max(tdr['distance']), 0)

    def test_plot_tdr_returns_figure(self):
        content = """# GHz S RI R 50\n1 1 0 0 0 0 0 1 0\n"""
        data = plotting_utils.load_touchstone(StringIO(content))
        tdr = plotting_utils.compute_tdr_trace(data, parameter=(1, 1), points=128, window='none')
        fig = plotting_utils.plot_tdr(tdr, show_impedance=True)
        self.assertEqual(len(fig.axes), 2)


class TestPlotLineRegression(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({
            'time': [0, 1, 2, 3],
            'voltage': [0.1, 0.2, 0.3, 0.4],
            'current': [1.0, 1.1, 1.2, 1.3],
        })

    def tearDown(self):
        plt.close('all')

    def test_plot_line_allows_duplicate_axis_selection(self):
        fig = plotting_utils.plot_line(self.df, 'time', ['time'])
        self.assertIsNotNone(fig)
        self.assertGreater(len(fig.axes), 0)
        plt.close(fig)

    def test_plot_line_supports_log_axes(self):
        fig = plotting_utils.plot_line(
            self.df,
            x_col='time',
            y_cols=['voltage'],
            logx=True,
            logy=True,
        )
        ax = fig.axes[0]
        self.assertEqual(ax.get_xscale(), 'log')
        self.assertEqual(ax.get_yscale(), 'log')
        plt.close(fig)

    def test_plot_line_handles_grouping_column_matching_axis(self):
        df = pd.DataFrame({
            'group_id': [0, 0, 1, 1],
            'metric': [5, 6, 7, 8],
        })
        fig = plotting_utils.plot_line(
            df,
            x_col='group_id',
            y_cols=['metric'],
            group_col='group_id',
        )
        self.assertIsNotNone(fig)
        self.assertGreater(len(fig.axes), 0)
        plt.close(fig)


if __name__ == '__main__':
    unittest.main()
