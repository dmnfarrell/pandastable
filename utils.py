import pandas as pd
import re
import numpy as np
from datetime import datetime
import os

def load_csv_file(file_path):
    """Load CSV file with error handling."""
    try:
        # Try to read the file with various encodings
        encodings = ['utf-8', 'latin1', 'ISO-8859-1', 'cp1252', 'utf-16']
        for encoding in encodings:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                return df
            except Exception:
                continue

        # Try with Python engine
        return pd.read_csv(file_path, encoding='utf-8', engine='python', on_bad_lines='skip')
    except Exception as e:
        raise Exception(f"Failed to load file: {e}")

def apply_row_filter(df, filter_text):
    """
    Apply advanced row filtering to the DataFrame.
    Supports:
    1. Pandas query filtering (e.g., "column > 100")
    2. Text-based contains search (e.g., "error")
    3. Mixing query and contains search using '@' separator (e.g., "col > 10 @ error")
    4. Wildcard '*' to show non-matching rows (e.g., "search *")
    """
    if not filter_text or df.empty:
        return df

    try:
        # Check for wildcard pattern first
        if ' *' in filter_text or filter_text.endswith('*'):
            base_search = filter_text.split('*')[0].strip()
            base_matches = _row_filter_impl(df, base_search)
            non_matches = df[~df.index.isin(base_matches.index)]

            if len(non_matches) > 0:
                return pd.concat([base_matches, non_matches])
            return base_matches
        else:
            return _row_filter_impl(df, filter_text)
    except Exception as e:
        print(f"Error in row filter: {e}")
        return df

def _row_filter_impl(df, filter_text):
    """Helper method for row filtering."""
    if not filter_text:
        return df

    query_part = ''
    contains_part = ''

    if '@' in filter_text:
        query_part, contains_part = [part.strip() for part in filter_text.split('@', 1)]
    else:
        query_part = filter_text

    filtered_df = df.copy()

    # Apply query filtering
    query_successful = False
    if query_part:
        try:
            filtered_df = filtered_df.query(query_part)
            query_successful = True
        except Exception:
            query_successful = False

    # Apply contains filtering
    if contains_part and query_successful:
        filtered_df = _apply_single_filter(filtered_df, contains_part)
    elif not query_successful and contains_part:
        filtered_df = _apply_single_filter(df, contains_part)
    elif not query_successful and not contains_part:
        filtered_df = _apply_single_filter(df, query_part)

    return filtered_df

def _apply_single_filter(df, search_text):
    """Helper to apply text search filter."""
    if not search_text:
        return df

    try:
        # List pattern [term1, term2]
        if search_text.startswith('[') and search_text.endswith(']'):
            list_terms = [t.strip() for t in search_text[1:-1].split(',') if t.strip()]
            if list_terms:
                str_df = df.astype(str)
                mask = str_df.apply(lambda x: any(
                    x.str.contains(re.escape(term), case=False, na=False, regex=False).any()
                    for term in list_terms
                ), axis=1)
                return df[mask].copy()
            return df

        # Exclusion !term
        if search_text.startswith('!'):
            exclude_text = search_text[1:]
            if (exclude_text.startswith('"') and exclude_text.endswith('"')) or \
               (exclude_text.startswith("'") and exclude_text.endswith("'")):
                exact_text = exclude_text[1:-1]
                str_df = df.astype(str)
                mask = ~str_df.apply(lambda x: x == exact_text).any(axis=1)
            else:
                str_df = df.astype(str)
                mask = ~str_df.apply(lambda x: x.str.contains(re.escape(exclude_text), case=False, na=False)).any(axis=1)
        # Exact match "term"
        elif (search_text.startswith('"') and search_text.endswith('"')) or \
             (search_text.startswith("'") and search_text.endswith("'")):
            exact_text = search_text[1:-1]
            str_df = df.astype(str)
            mask = str_df.apply(lambda x: x == exact_text).any(axis=1)
        # Regex anchors
        elif search_text.startswith('^') or search_text.endswith('$'):
            str_df = df.astype(str)
            if search_text.startswith('^'):
                pattern = f'^{re.escape(search_text[1:])}'
            else:
                pattern = f'{re.escape(search_text[:-1])}$'
            mask = str_df.apply(lambda x: x.str.contains(pattern, case=False, na=False, regex=True)).any(axis=1)
        # Normal contains
        else:
            terms = [t.strip() for t in search_text.split() if t.strip()]
            str_df = df.astype(str)
            if len(terms) > 1:
                mask = str_df.apply(lambda x: all(
                    x.str.contains(re.escape(term), case=False, na=False).any()
                    for term in terms
                ), axis=1)
            else:
                mask = str_df.apply(lambda x: x.str.contains(re.escape(search_text), case=False, na=False)).any(axis=1)

        return df[mask].copy()
    except Exception:
        return df

def apply_column_filter(df, filter_text):
    """
    Filter DataFrame columns based on filter text.
    Supports:
    - Multiple terms separated by space/comma/semicolon
    - Quotes for exact match
    - ! for exclusion
    - * for wildcard (include remaining)
    """
    if not filter_text:
        return df

    filter_terms = [term.strip() for term in filter_text.replace(',', ' ').replace(';', ' ').split()]
    filter_terms = [term for term in filter_terms if term]

    if not filter_terms:
        return df

    all_columns = df.columns.tolist()
    include_remaining = "*" in filter_terms
    if include_remaining:
        filter_terms.remove("*")

    # If all terms are exclusions, imply wildcard
    if filter_terms and all(term.startswith('!') for term in filter_terms):
        include_remaining = True

    include_columns = []
    exclude_columns = set()

    for term in filter_terms:
        term = term.strip()
        if not term:
            continue

        exclude = term.startswith('!')
        if exclude:
            term = term[1:].strip()
            if not term:
                continue

        exact_match = False
        if (term.startswith('"') and term.endswith('"')) or (term.startswith("'") and term.endswith("'")):
            exact_match = True
            term = term[1:-1]
            if not term:
                continue

        for col in all_columns:
            col_lower = str(col).lower()
            term_lower = term.lower()

            matches = (term_lower == col_lower) if exact_match else (term_lower in col_lower)

            if matches:
                if exclude:
                    exclude_columns.add(col)
                elif col not in include_columns:
                    include_columns.append(col)

    if include_remaining:
        remaining = [col for col in all_columns if col not in include_columns and col not in exclude_columns]
        include_columns.extend(remaining)

    final_columns = [col for col in include_columns if col not in exclude_columns]

    if not final_columns:
        return df

    return df[final_columns]
