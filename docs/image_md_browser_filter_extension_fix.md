# Image/MD Browser: combined text + extension filtering fix

## Problem

The file filter in `examples/image_MD_browser_Gemini-chat_v3.16_filter.py` previously treated the filter entry as a single substring search across the table, with one special-case:

- If the query started with `.` (example: `.png`), it was treated as a file-extension match.

This broke mixed queries such as:

- `map .png`

Because the old logic did not detect `.png` as an extension token when it appeared after other text. Instead, it attempted to find the literal substring `"map .png"` across the table, which usually matches nothing.

## Fix

`filter_images()` now tokenizes the query and separates:

- Extension tokens: any whitespace-delimited token that starts with `.` (example: `.png`, `.jpg`)
- Text tokens: all other tokens

Filtering behavior is:

- Extension tokens are combined with **OR** (file name ends with any of the listed extensions)
- Text tokens are combined with **AND** (each text token must appear somewhere in the row across any column)
- If both extension + text tokens are present, the final result is combined with **AND**

In other words:

- `map .png` => (contains `map`) AND (endswith `.png`)

## Examples

- Query: `.png`
  - Result: all rows where `Name` ends with `.png`

- Query: `map`
  - Result: all rows where any column contains `map` (case-insensitive)

- Query: `map .png`
  - Result: rows containing `map` in any column AND filename ends with `.png`

- Query: `.png .jpg`
  - Result: filenames ending with `.png` OR `.jpg`

- Query: `map test .png`
  - Result: rows containing `map` AND `test` AND filename ends with `.png`

## Implementation details

File:

- `examples/image_MD_browser_Gemini-chat_v3.16_filter.py`

Core change:

- Replace the previous `q.startswith('.')` special-case with token-based parsing and mask composition using Pandas.
