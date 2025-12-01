# PRD: CSV Browser Filter Function Fixes

## Overview
This document outlines bugs and issues identified in the row and column filter functions of `csv_browser_v6.x1.2_search_columns.py`. Each issue is prioritized and includes a clear fix specification.

---

## Issue Tracker

| ID | Priority | Issue | Status |
|----|----------|-------|--------|
| F1 | P0 | Duplicate exception block (dead code) | Pending |
| F2 | P0 | Undefined `filtered_df` variable | Pending |
| F3 | P1 | Missing newline between functions | Pending |
| F4 | P2 | Recursive call risk in reset_column_filter | Pending |
| F5 | P2 | Query fallback behavior unclear | Pending |
| F6 | P2 | Index restoration logic flaw | Pending |
| F7 | P2 | Stale filtered_csv_df state | Pending |

---

## P0 - Critical Bugs

### F1: Duplicate Exception Block in `_apply_single_filter`

**Location**: Lines 1102-1110

**Current Code**:
```python
        except Exception as e:
            print(f"Error in _apply_single_filter: {e}")
            traceback.print_exc()
            return df
            
        except Exception as e:
            print(f"Error in _apply_filter: {e}")
            traceback.print_exc()
            return df
```

**Problem**: 
- Two consecutive `except` blocks - the second is unreachable dead code
- Second block references wrong function name (`_apply_filter` doesn't exist)
- This is likely a copy-paste error from a previous refactor

**Fix**:
Remove lines 1107-1110 (the second `except` block).

**Verification**:
- Run the app and apply various row filters
- Confirm no syntax errors or unexpected behavior

---

### F2: Undefined `filtered_df` Variable in `_apply_column_filter`

**Location**: Lines 4165-4186

**Current Code**:
```python
                if not valid_columns:
                    print("No valid columns for this file, showing all columns")
                    self.csv_table.model.df = self.original_csv_df.copy()
                else:
                    # Apply column filter
                    filtered_df = self.original_csv_df.loc[:, valid_columns].copy()
                    ...
                    self.csv_table.model.df = filtered_df
                
                # Redraw the table
                self.csv_table.redraw()
                
                ...
                # Check if index was reset and restore it if needed
                if not self.csv_table.model.df.index.equals(filtered_df.index):  # ERROR: filtered_df undefined!
```

**Problem**:
- When `valid_columns` is empty, `filtered_df` is never defined
- Line 4186 references `filtered_df` unconditionally, causing `NameError`

**Fix**:
Define `filtered_df` in both branches:
```python
                if not valid_columns:
                    print("No valid columns for this file, showing all columns")
                    filtered_df = self.original_csv_df.copy()
                else:
                    filtered_df = self.original_csv_df.loc[:, valid_columns].copy()
                
                self.csv_table.model.df = filtered_df
```

**Verification**:
- Load a CSV file
- Apply a column filter that matches no columns (e.g., `zzzznonexistent`)
- Confirm no `NameError` occurs

---

## P1 - Code Quality Issues

### F3: Missing Newline Between Functions

**Location**: Lines 700-701

**Current Code**:
```python
                self.update_file_dataframe()
    def on_key_press(self, event):
```

**Problem**:
- PEP 8 requires two blank lines between top-level function/class definitions
- Missing blank line suggests possible merge/edit error

**Fix**:
Add blank line after `filter_files` method:
```python
                self.update_file_dataframe()

    def on_key_press(self, event):
```

**Verification**:
- Run linter (flake8/pylint)
- Visual inspection

---

## P2 - Improvements

### F4: Recursive Call Risk in `reset_column_filter`

**Location**: Lines 4248-4271

**Current Code**:
```python
    def reset_column_filter(self):
        ...
        # Clear the filter text
        self.column_filter_var.set("")  # This triggers filter_columns callback!
```

**Problem**:
- Setting `column_filter_var` to `""` triggers the trace callback `filter_columns`
- `filter_columns` calls `reset_column_filter()` when filter text is empty
- Creates potential infinite recursion (currently mitigated by early return)

**Fix**:
Add a guard flag to prevent recursive calls:
```python
    def reset_column_filter(self):
        if getattr(self, '_resetting_column_filter', False):
            return
        self._resetting_column_filter = True
        try:
            ...
            self.column_filter_var.set("")
        finally:
            self._resetting_column_filter = False
```

**Verification**:
- Clear column filter multiple times rapidly
- Confirm no recursion errors or stack overflow

---

### F5: Query Fallback Behavior Unclear

**Location**: Lines 1240-1243 in `row_filter_impl`

**Current Code**:
```python
        elif not query_successful and not contains_part:
            print(f"Query failed, falling back to contains search for: '{query_part}'")
            filtered_df = self._apply_single_filter(df, query_part)
```

**Problem**:
- When pandas query fails (e.g., `column > 5`), it silently falls back to text search
- User might expect an error, not a search for literal string "column > 5"
- No visual feedback that query failed

**Fix Options**:
1. **Option A (Recommended)**: Show status message when query fails
   ```python
   elif not query_successful and not contains_part:
       print(f"Query failed, falling back to contains search for: '{query_part}'")
       if hasattr(self, 'status_var'):
           self.status_var.set(f"Query syntax invalid, searching as text: '{query_part}'")
       filtered_df = self._apply_single_filter(df, query_part)
   ```

2. **Option B**: Don't fallback, show error instead
   ```python
   elif not query_successful and not contains_part:
       if hasattr(self, 'status_var'):
           self.status_var.set(f"Invalid query: '{query_part}'. Use @ for text search.")
       return df  # Return unfiltered
   ```

**Verification**:
- Enter invalid query like `column > 5` (where column doesn't exist)
- Confirm appropriate feedback is shown

---

### F6: Index Restoration Logic Flaw

**Location**: Lines 3989-4000 in `filter_columns`

**Current Code**:
```python
                if current_index is not None:
                    current_df = self.csv_table.model.df
                    if len(current_df) == len(current_index):
                        try:
                            current_df.index = current_index
```

**Problem**:
- Assumes length equality means rows are the same
- After row filtering + column filtering, index could be misaligned
- Could assign wrong index to wrong rows

**Fix**:
Remove the index restoration logic in `filter_columns` - column filtering should not change row indices:
```python
                # Column filtering doesn't change rows, so index should be preserved automatically
                # Remove the manual index restoration which can cause misalignment
```

Or use a more robust check:
```python
                # Only restore if the index values actually match
                if current_index is not None and len(current_df) == len(current_index):
                    if set(current_df.index) == set(current_index):
                        current_df.index = current_index
```

**Verification**:
- Apply row filter first, then column filter
- Confirm row indices remain correct

---

### F7: Stale `filtered_csv_df` State

**Location**: Lines 1164-1165 in `row_filter`

**Current Code**:
```python
            # Store the filtered DataFrame for column filtering
            self.filtered_csv_df = filtered_df
```

**Problem**:
- `filtered_csv_df` is set even when filter returns empty or errors occur later
- Stale state could cause issues in `_apply_column_filter_to_filtered_data()`

**Fix**:
Only set `filtered_csv_df` after successful filtering:
```python
            # Store the filtered DataFrame for column filtering (only if valid)
            if filtered_df is not None and not filtered_df.empty:
                self.filtered_csv_df = filtered_df
            elif not filter_text:  # No filter, use original
                self.filtered_csv_df = self.original_csv_df.copy()
```

**Verification**:
- Apply filter that returns no results
- Then apply column filter
- Confirm no errors and appropriate empty state shown

---

## Implementation Order

1. **F1** - Remove duplicate exception block (simple, high impact)
2. **F2** - Fix undefined variable (prevents crashes)
3. **F3** - Add missing newline (trivial)
4. **F4** - Add recursion guard (defensive)
5. **F5** - Improve query fallback feedback (UX)
6. **F6** - Fix index restoration logic (data integrity)
7. **F7** - Fix stale state handling (robustness)

---

## Testing Checklist

- [ ] F1: Apply various row filters, confirm no errors
- [ ] F2: Apply column filter with no matches, confirm no NameError
- [ ] F3: Run linter, confirm no style warnings
- [ ] F4: Rapidly clear/set column filter, confirm no recursion
- [ ] F5: Enter invalid query, confirm feedback shown
- [ ] F6: Apply row filter then column filter, confirm indices correct
- [ ] F7: Apply filter with no results, then column filter, confirm no errors
