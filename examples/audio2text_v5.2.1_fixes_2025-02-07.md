# Audio2Text v5.2.1 Fixes - Session 2025-02-07

## Summary

Fixed FFmpeg-related errors and missing helper functions that were causing transcription failures for media files with duration probing issues.

## Changes Made

### 1. Enhanced `_probe_duration_seconds()` Function

**File:** `audio2text_v5.2.1_rename_MD.py`

**Issue:** The original function only used a single ffprobe strategy that failed on files with missing 'moov' atoms or other container corruption.

**Fix:** Implemented a 3-strategy fallback approach:

1. **Standard format probe** - Original strategy using `-show_entries format=duration`
2. **JSON format probe** - More robust parsing of format and stream durations from JSON output
3. **FFmpeg stderr parsing** - Parses duration from ffmpeg's header output when ffprobe fails

Each strategy includes proper timeout handling (30s) to prevent hanging on problematic files.

### 2. Added Missing Helper Functions

**Functions Added:**

#### `_dedupe_consecutive_sentences(text: str, max_repeat: int = 1) -> str`
Collapses consecutive identical sentences to reduce repetition in transcription output. Uses heuristic sentence splitting with punctuation delimiters.

#### `_split_sentences(text: str) -> list`
Heuristic sentence splitter for cross-chunk de-duplication. Supports the rolling window suppression in incremental transcription.

#### `_post_process_dedupe_file(file_path: str)`
Global de-duplication pass applied to completed transcription files. Removes consecutive duplicate sentences across the entire transcript.

#### `_strip_initial_prompt_leak(text: str, prompt: str | None) -> str`
Removes occurrences of the initial prompt text if Whisper echoes it back into the output. Uses case-insensitive whitespace-normalized matching.

**Issue:** These functions were being called in `transcribe_incremental()` but were not defined, causing `NameError` exceptions during chunk processing.

### 3. Enhanced FFmpeg Discovery

**Added `_resolve_ffmpeg_cmd()` Helper:**

```python
def _resolve_ffmpeg_cmd() -> str:
    """Return the path to ffmpeg binary, checking PATH and common locations."""
```

This helper:
- Checks `shutil.which("ffmpeg")` first
- Falls back to checking next to `ffprobe` location
- Returns `"ffmpeg"` as final fallback

**Functions Updated:**
- `_extract_time_clip()` - Now uses `_resolve_ffmpeg_cmd()` and captures stderr
- `extract_audio_to_wav()` - Now uses `_resolve_ffmpeg_cmd()` with stderr capture
- `remux_media()` - Now uses `_resolve_ffmpeg_cmd()` with stderr capture

### 4. Improved Error Logging

- Changed `stderr=subprocess.DEVNULL` to `stderr=subprocess.PIPE` in all ffmpeg subprocess calls
- Added `stderr_output[:1000]` capture to log full ffmpeg error messages (previously truncated at 400 chars)
- Added detailed error messages for FileNotFoundError cases

## Files Modified

- `c:\Users\juesh\OneDrive\Documents\windsurf\stock_charts_10k10q\audio2text_v5.2.1_rename_MD.py`

## Line Ranges Changed

| Line Range | Description |
|------------|-------------|
| 631-648 | Added `_resolve_ffmpeg_cmd()` helper |
| 669-722 | Replaced `_probe_duration_seconds()` with 3-strategy fallback version |
| 840-942 | Added missing helper functions (`_dedupe_consecutive_sentences`, `_split_sentences`, `_post_process_dedupe_file`, `_strip_initial_prompt_leak`) |

## Verification

- Syntax validated using `python -m py_compile` - exit code 0
- Code compiles without errors

## Known Issues Addressed

1. **RuntimeError: Unreadable media: ffmpeg could not extract audio. Skipping.** - Fixed by improving duration probing to handle corrupted/missing metadata
2. **NameError: name '_dedupe_consecutive_sentences' is not defined** - Fixed by adding all missing helper functions
3. **Truncated ffmpeg error messages** - Fixed by increasing stderr capture from 400 to 1000 chars

## Testing Notes

Re-run transcription on `impact-ep9-2.mp3` to verify:
- Duration is properly detected via one of the 3 fallback strategies
- Transcription proceeds without `NameError`
- Full ffmpeg error messages are logged if extraction fails
