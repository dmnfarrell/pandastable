import streamlit as st
import pandas as pd
import os
import utils
import plotting_utils
import numpy as np

st.set_page_config(layout="wide", page_title="CSV Browser")

# --- Session State Initialization ---
if 'current_dir' not in st.session_state:
    st.session_state.current_dir = os.getcwd()
if 'file_filter' not in st.session_state:
    st.session_state.file_filter = ""
if 'selected_file' not in st.session_state:
    st.session_state.selected_file = None
if 'df' not in st.session_state:
    st.session_state.df = None

# --- Sidebar: File Browser ---
st.sidebar.title("File Browser")

# Directory Selection
new_dir = st.sidebar.text_input("Current Directory", st.session_state.current_dir)
if os.path.isdir(new_dir):
    st.session_state.current_dir = new_dir
else:
    st.sidebar.error("Invalid directory")

# File Filter
st.session_state.file_filter = st.sidebar.text_input("Filter Files", st.session_state.file_filter)

# List Files
try:
    files = [f for f in os.listdir(st.session_state.current_dir)
             if f.lower().endswith(('.csv', '.tsv'))]

    # Filter files
    if st.session_state.file_filter:
        terms = st.session_state.file_filter.lower().split()
        filtered_files = []
        for f in files:
            match = True
            for term in terms:
                if term.startswith('!'):
                    if term[1:] in f.lower():
                        match = False
                        break
                elif term not in f.lower():
                    match = False
                    break
            if match:
                filtered_files.append(f)
        files = filtered_files

    # Create File DataFrame for display
    if files:
        file_data = []
        for f in files:
            path = os.path.join(st.session_state.current_dir, f)
            stat = os.stat(path)
            file_data.append({
                "Name": f,
                "Size": f"{stat.st_size / 1024:.1f} KB",
                "Modified": pd.to_datetime(stat.st_mtime, unit='s').strftime('%Y-%m-%d %H:%M')
            })
        file_df = pd.DataFrame(file_data)

        # File Selection
        selected_row = st.sidebar.dataframe(
            file_df,
            selection_mode="single-row",
            on_select="rerun",
            hide_index=True
        )

        if selected_row and len(selected_row.selection.rows) > 0:
            idx = selected_row.selection.rows[0]
            filename = file_df.iloc[idx]["Name"]
            filepath = os.path.join(st.session_state.current_dir, filename)

            if st.session_state.selected_file != filepath:
                st.session_state.selected_file = filepath
                try:
                    st.session_state.df = utils.load_csv_file(filepath)
                except Exception as e:
                    st.error(f"Error loading file: {e}")
                    st.session_state.df = None

except Exception as e:
    st.sidebar.error(f"Error listing files: {e}")

# --- Main Content ---
if st.session_state.selected_file and st.session_state.df is not None:
    st.title(f"Viewing: {os.path.basename(st.session_state.selected_file)}")

    # --- Filters ---
    with st.expander("Filters", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            row_filter = st.text_input("Row Filter (query, text, @)", help="e.g., 'col > 10', 'error', 'col > 10 @ error'")
        with col2:
            col_filter = st.text_input("Column Filter", help="Space/comma separated. !exclude, *wildcard")

        filtered_df = st.session_state.df.copy()

        # Apply Row Filter
        if row_filter:
            try:
                filtered_df = utils.apply_row_filter(filtered_df, row_filter)
            except Exception as e:
                st.error(f"Row filter error: {e}")

        # Apply Column Filter
        if col_filter:
            try:
                filtered_df = utils.apply_column_filter(filtered_df, col_filter)
            except Exception as e:
                st.error(f"Column filter error: {e}")

    # --- Data Viewer ---
    st.dataframe(filtered_df, use_container_width=True)
    st.caption(f"Showing {len(filtered_df)} rows, {len(filtered_df.columns)} columns")

    # --- Plotting ---
    st.divider()
    st.subheader("Plotting")

    tabs = st.tabs(["General Plots", "Correlation Analysis", "Special Plots"])

    numeric_cols = plotting_utils.get_numeric_varying_columns(filtered_df)
    all_cols = filtered_df.columns.tolist()

    with tabs[0]: # General Plots
        plot_type = st.selectbox("Plot Type", ["Scatter", "Line", "Histogram", "Bar"])

        if plot_type == "Scatter":
            col1, col2, col3 = st.columns(3)
            x_col = col1.selectbox("X Axis", numeric_cols)
            y_col = col2.selectbox("Y Axis", numeric_cols, index=1 if len(numeric_cols) > 1 else 0)
            c_col = col3.selectbox("Color", [None] + numeric_cols)

            if st.button("Generate Scatter Plot"):
                fig = plotting_utils.plot_scatter(filtered_df, x_col, y_col, c_col)
                st.pyplot(fig)

        elif plot_type == "Line":
            col1, col2 = st.columns(2)
            x_col = col1.selectbox("X Axis", numeric_cols, key="line_x")
            y_cols = col2.multiselect("Y Axis", numeric_cols, default=[numeric_cols[1]] if len(numeric_cols) > 1 else [])

            if st.button("Generate Line Plot"):
                fig = plotting_utils.plot_line(filtered_df, x_col, y_cols)
                st.pyplot(fig)

        elif plot_type == "Histogram":
            col = st.selectbox("Column", numeric_cols, key="hist_col")
            bins = st.slider("Bins", 5, 100, 20)
            if st.button("Generate Histogram"):
                fig = plotting_utils.plot_histogram(filtered_df, col, bins)
                st.pyplot(fig)

    with tabs[1]: # Correlation Analysis
        target_col = st.selectbox("Target Column", numeric_cols, key="corr_target")
        top_n = st.number_input("Top N", 1, 20, 5)

        if st.button("Analyze Correlations"):
            corr_df, _ = plotting_utils.get_top_correlated_columns(filtered_df, target_col, top_n)
            if corr_df is not None:
                st.dataframe(corr_df)

                # Show top correlation plot
                if not corr_df.empty:
                    top_corr_col = corr_df.iloc[0]['Column']
                    top_corr_val = corr_df.iloc[0]['Correlation']
                    st.write(f"Top correlation: {top_corr_col} ({top_corr_val:.3f})")
                    fig = plotting_utils.plot_correlation(filtered_df, target_col, top_corr_col, top_corr_val)
                    st.pyplot(fig)

    with tabs[2]: # Special Plots
        special_type = st.selectbox("Special Plot Type", ["Shmoo", "Bathtub", "Eye Diagram"])

        if special_type == "Shmoo":
            col1, col2, col3 = st.columns(3)
            x_p = col1.selectbox("X Param", numeric_cols, key="shmoo_x")
            y_p = col2.selectbox("Y Param", numeric_cols, key="shmoo_y")
            z_p = col3.selectbox("Z Param", numeric_cols, key="shmoo_z")

            col4, col5 = st.columns(2)
            t_min = col4.text_input("Threshold Min", "")
            t_max = col5.text_input("Threshold Max", "")

            t_min_val = float(t_min) if t_min else None
            t_max_val = float(t_max) if t_max else None

            if st.button("Generate Shmoo Plot"):
                fig = plotting_utils.plot_shmoo(filtered_df, x_p, y_p, z_p, t_min_val, t_max_val)
                st.pyplot(fig)

        elif special_type == "Bathtub":
            col1, col2 = st.columns(2)
            x_b = col1.selectbox("X Axis (Sample Point)", numeric_cols, key="bath_x")
            y_b = col2.multiselect("Y Axis (BER)", numeric_cols, key="bath_y")
            target = st.text_input("BER Target", "1e-12")

            if st.button("Generate Bathtub Plot"):
                fig = plotting_utils.plot_bathtub(filtered_df, x_b, y_b, float(target))
                st.pyplot(fig)

        elif special_type == "Eye Diagram":
            col1, col2 = st.columns(2)
            t_col = col1.selectbox("Time Column", numeric_cols, key="eye_t")
            v_col = col2.selectbox("Voltage Column", numeric_cols, key="eye_v")
            ui = st.slider("UI Width", 0.5, 2.0, 1.0)

            if st.button("Generate Eye Diagram"):
                fig = plotting_utils.plot_eye(filtered_df, t_col, v_col, ui)
                st.pyplot(fig)

else:
    st.info("Select a CSV file from the sidebar to view.")
