# Image Browser Table Column Updates

File:
`examples/image_MD_browser_Gemini-chat_v3.13_file_op_menu.py`

## Requested changes
- Reduce the width of the `Name` column by ~5 characters.
- Move the `Date_Modified` column before the `Size` column.

## Implemented changes
### 1) Column order (`Date_Modified` before `Size`)
Location:
`ImageBrowser.setup_file_browser()`

- When building the records for `self.df`, the record dict order was changed to:
  - `Name`
  - `Date_Modified`
  - `Size`
  - `File_Path`

- Additionally, a DataFrame reordering step was added to enforce the preferred order even when dynamic `Field_*` columns exist:
  - Preferred: `['Name', 'Date_Modified', 'Size', 'File_Path']`
  - Remaining columns (e.g. `Field_1`, `Field_2`, ...) are appended after the preferred columns.

### 2) Reduce `Name` column width by ~5 characters
Location:
`ImageBrowser.setup_file_browser()` after:
`self.table = Table(...)` and `self.table.show()`

- Adjusts `self.table.columnwidths['Name']` by subtracting `5 * char_w`
  - `char_w` is estimated via `self.table.getScale()` (fallback to `8`)
- Enforces a minimum width using `self.table.cellwidth` (fallback `80`)
- Calls `self.table.setColPositions()` to apply the updated width.

## Notes
- The `Name` width adjustment is applied immediately after creating the table.
- Column order change affects the DataFrame column order, which pandastable uses for display.
