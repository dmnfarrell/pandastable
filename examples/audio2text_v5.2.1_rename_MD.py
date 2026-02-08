import whisper
import os
import json
import subprocess
import sys
import threading
import traceback
import base64
import tempfile
import shutil
import math
import urllib.parse
from typing import Optional

import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import simpledialog
from tkinter import ttk
from tkinter import font as tkfont
from datetime import datetime

def install_ffmpeg():
    try:
        # Try to import ffmpeg-python
        import ffmpeg
    except ImportError:
        print("Installing ffmpeg-python...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "ffmpeg-python"])
        import ffmpeg

def ensure_ffmpeg_in_path():
    """Ensure the ffmpeg executable is available by checking common Windows locations,
    falling back to a portable binary from imageio-ffmpeg, and validating availability.
    """

    def _validate_binary(binary_name: str) -> bool:
        try:
            subprocess.run([binary_name, "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return True
        except Exception:
            return False

    def _ensure_portable_ffmpeg() -> Optional[str]:
        """Use imageio-ffmpeg's bundled binary as a last resort."""
        try:
            import imageio_ffmpeg  # type: ignore
        except Exception:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "imageio-ffmpeg"])
                import imageio_ffmpeg  # type: ignore
            except Exception:
                return None
        try:
            ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            return None
        if not ffmpeg_path or not os.path.isfile(ffmpeg_path):
            return None

        ffmpeg_dir = os.path.dirname(ffmpeg_path)
        shim_path = os.path.join(ffmpeg_dir, "ffmpeg.exe")
        if os.path.isfile(shim_path):
            return shim_path

        try:
            shutil.copy2(ffmpeg_path, shim_path)
            return shim_path
        except Exception:
            # Fall back to the original filename even if it isn't named ffmpeg.exe
            return ffmpeg_path

    if _validate_binary("ffmpeg"):
        if not _validate_binary("ffprobe"):
            print("\nWarning: ffprobe not found. Audio stream list will show only 'Auto'.")
            print("Install an FFmpeg build that includes ffprobe and ensure its bin is on PATH.")
        return

    candidates = [
        r"C:\ffmpeg\bin",
        r"C:\Program Files\ffmpeg\bin",
        r"C:\Program Files (x86)\ffmpeg\bin",
        os.path.join(os.getcwd(), "ffmpeg", "bin"),
    ]

    for path in candidates:
        if path and os.path.isdir(path) and os.path.isfile(os.path.join(path, "ffmpeg.exe")):
            os.environ["PATH"] = path + os.pathsep + os.environ.get("PATH", "")
            if _validate_binary("ffmpeg"):
                break

    if not _validate_binary("ffmpeg"):
        portable_ffmpeg = _ensure_portable_ffmpeg()
        if portable_ffmpeg and os.path.isfile(portable_ffmpeg):
            portable_bin = os.path.dirname(portable_ffmpeg)
            os.environ["PATH"] = portable_bin + os.pathsep + os.environ.get("PATH", "")
            print(f"Using bundled FFmpeg from: {portable_ffmpeg}")

    if not _validate_binary("ffmpeg"):
        print("\nError: FFmpeg executable not found.")
        print("I looked for ffmpeg in the following locations:")
        for p in candidates:
            print(f" - {p}")
        print("\nTried installing imageio-ffmpeg but could not access a working binary.")
        print("Please ensure FFmpeg is installed and that its bin folder is added to your PATH.")
        print("Download: https://ffmpeg.org/download.html or a Windows build from https://www.gyan.dev/ffmpeg/builds/")
        sys.exit(1)

    if not _validate_binary("ffprobe"):
        print("\nWarning: ffprobe not found. Audio stream list will show only 'Auto'.")
        print("Install an FFmpeg build that includes ffprobe and ensure its bin is on PATH.")

def ensure_yt_dlp_installed():
    try:
        import yt_dlp  # noqa: F401
    except Exception:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])  # actively maintained fork
            import yt_dlp  # noqa: F401
        except Exception:
            print("Failed to install yt-dlp. URL transcription for online videos may not work.")
            return False
    return True

def main():
    # Install required packages and ensure ffmpeg availability
    install_ffmpeg()
    ensure_ffmpeg_in_path()

    # Force-install Send2Trash so deletions go to Recycle Bin
    try:
        import send2trash  # noqa: F401
    except Exception:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "Send2Trash"])  # canonical package name
            import send2trash  # noqa: F401
        except Exception:
            # Continue without hard-failing; deletion code will fall back if needed
            pass

    # Try to prepare Markdown rendering deps (markdown + tkhtmlview) and optional rich features
    def ensure_md_preview_deps():
        md_mod = None
        md_render = None
        html_label_cls = None
        try:
            import markdown as _md
            md_mod = _md
            try:
                md_render = _md.markdown
            except Exception:
                md_render = None
        except Exception:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "markdown"]) 
                import markdown as _md
                md_mod = _md
                try:
                    md_render = _md.markdown
                except Exception:
                    md_render = None
            except Exception:
                md_mod = None
                md_render = None
        try:
            from tkhtmlview import HTMLLabel as _HTMLLabel
            html_label_cls = _HTMLLabel
        except Exception:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "tkhtmlview"]) 
                from tkhtmlview import HTMLLabel as _HTMLLabel
                html_label_cls = _HTMLLabel
            except Exception:
                html_label_cls = None
        return md_mod, md_render, html_label_cls

    md_module, md_render, HTMLLabel = ensure_md_preview_deps()
    # Try to enable a richer HTML renderer if available
    HtmlFrame = None
    try:
        from tkinterweb import HtmlFrame as _HtmlFrame
        HtmlFrame = _HtmlFrame
    except Exception:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "tkinterweb"]) 
            from tkinterweb import HtmlFrame as _HtmlFrame
            HtmlFrame = _HtmlFrame
        except Exception:
            HtmlFrame = None
    # Optional richer Markdown features
    pygments_formatter = None
    has_pymdown = False
    try:
        # Syntax highlighting
        from pygments.formatters import HtmlFormatter as _HtmlFormatter
        pygments_formatter = _HtmlFormatter()
    except Exception:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "Pygments"]) 
            from pygments.formatters import HtmlFormatter as _HtmlFormatter
            pygments_formatter = _HtmlFormatter()
        except Exception:
            pygments_formatter = None
    try:
        import pymdownx  # noqa: F401
        has_pymdown = True
    except Exception:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pymdown-extensions"]) 
            import pymdownx  # noqa: F401
            has_pymdown = True
        except Exception:
            has_pymdown = False

    # Load Whisper model once with retry on checksum mismatch
    def _whisper_model_path(cache_dir: str, name: str) -> str:
        try:
            return os.path.join(cache_dir, f"{name}.pt")
        except Exception:
            return ""

    def _remove_cached_model(cache_dir: str, name: str):
        try:
            p = _whisper_model_path(cache_dir, name)
            if p and os.path.isfile(p):
                os.remove(p)
        except Exception:
            pass

    def load_whisper_model_with_retry(name: str = "small"):
        print("Loading Whisper model (this may take a moment)...")
        primary_cache = os.path.join(os.path.expanduser("~"), ".cache", "whisper")
        alt_cache = os.path.join(os.getcwd(), "whisper_models_cache")
        try:
            os.makedirs(primary_cache, exist_ok=True)
        except Exception:
            pass
        try:
            os.makedirs(alt_cache, exist_ok=True)
        except Exception:
            pass
        # Attempt 1: use primary cache
        try:
            return whisper.load_model(name, download_root=primary_cache)
        except RuntimeError as e:
            if "checksum" not in str(e).lower():
                raise
            # Clear potentially corrupted file and try alt cache
            _remove_cached_model(primary_cache, name)
        # Attempt 2: alt cache, after clearing alt as well
        _remove_cached_model(alt_cache, name)
        return whisper.load_model(name, download_root=alt_cache)

    # Start with a lightweight model for quick startup; can be changed from UI
    model = load_whisper_model_with_retry("small")

    # Build GUI
    root = tk.Tk()
    root.title("Audio to Text (Whisper)")
    root.geometry("900x600")

    # UI Elements
    status_var = tk.StringVar(value="Ready. Click 'Select Audio' to transcribe.")
    current_file_var = tk.StringVar(value="No file selected.")
    output_path_var = tk.StringVar(value="")
    # Single status bar: file + status + model + legend
    status_bar_var = tk.StringVar(value="")
    def _refresh_status_bar(*_):
        try:
            cf = current_file_var.get() or ""
            st = status_var.get() or ""
            sep = "  |  " if (cf and st) else ""
            try:
                mdl = ("  |  " + (model_display_var.get() or "")) if model_display_var.get() else ""
            except Exception:
                mdl = ""
            legend = "  |  Legend: 🎥 video"
            status_bar_var.set(f"{cf}{sep}{st}{mdl}{legend}")
        except Exception:
            pass

    def set_status(message: str):
        try:
            status_var.set(str(message))
        except Exception:
            pass
        try:
            _refresh_status_bar()
        except Exception:
            pass
        try:
            root.update_idletasks()
        except Exception:
            pass
    try:
        # Keep status bar up-to-date automatically
        status_var.trace_add("write", _refresh_status_bar)
        current_file_var.trace_add("write", _refresh_status_bar)
        model_display_var.trace_add("write", _refresh_status_bar)
    except Exception:
        pass

    # header = tk.Label(root, text="Audio to Text", font=("Segoe UI", 12, "bold"))
    # header.pack(pady=(6, 2))

    frame = tk.Frame(root)
    frame.pack(fill=tk.X, padx=8)

    select_btn = tk.Button(frame, text="Select Audio", width=12)
    select_btn.pack(side=tk.LEFT)

    transcribe_url_btn = tk.Button(frame, text="Transcribe URL", width=14)
    transcribe_url_btn.pack(side=tk.LEFT, padx=(6, 0))

    browse_btn = tk.Button(frame, text="Browse Folder", width=12)
    browse_btn.pack(side=tk.LEFT, padx=(6, 0))

    transcribe_sel_btn = tk.Button(frame, text="Transcribe Selected", width=20)
    transcribe_sel_btn.pack(side=tk.LEFT, padx=(8, 0))

    # New: Extract-only and Transcribe-extracted actions
    extract_only_btn = tk.Button(frame, text="Extract Audio Only", width=18)
    extract_only_btn.pack(side=tk.LEFT, padx=(6, 0))

    # New: Remux Selected (container copy to fix moov atom issues)
    remux_btn = tk.Button(frame, text="Remux Selected", width=16)
    remux_btn.pack(side=tk.LEFT, padx=(6, 0))

    # Stream chooser: Auto or explicit audio stream per current selection
    stream_label = tk.Label(frame, text="Stream:")
    stream_label.pack(side=tk.LEFT, padx=(8, 2))
    audio_stream_choice_var = tk.StringVar(value="Auto")
    audio_stream_combo = ttk.Combobox(frame, textvariable=audio_stream_choice_var, values=["Auto"], width=28, state="readonly")
    audio_stream_combo.pack(side=tk.LEFT)
    # Map display string -> stream position (0-based among audio streams)
    audio_stream_map = {"Auto": None}

    # Manual refresh button to re-probe streams for the currently selected row
    refresh_streams_btn = tk.Button(frame, text="Refresh Streams", width=16)
    refresh_streams_btn.pack(side=tk.LEFT, padx=(6, 0))

    preview_stream_btn = tk.Button(frame, text="Preview Stream", width=16)
    preview_stream_btn.pack(side=tk.LEFT, padx=(6, 0))

    transcribe_extracted_btn = tk.Button(frame, text="Transcribe Extracted", width=18)
    transcribe_extracted_btn.pack(side=tk.LEFT, padx=(6, 0))

    auto_fit_btn = tk.Button(frame, text="Auto-fit Columns", width=14)
    auto_fit_btn.pack(side=tk.LEFT, padx=(6, 0))

    add_md_btn = tk.Button(frame, text="Add MD Only", width=14)
    add_md_btn.pack(side=tk.LEFT, padx=(8, 0))

    # Move group (audio/txt/md) for selected row
    move_group_btn = tk.Button(frame, text="Move Group", width=12)
    move_group_btn.pack(side=tk.LEFT, padx=(6, 0))

    # Initialize Tk variables now that root exists
    current_model_name = tk.StringVar(value="small")
    # Model display stringvar available to both toolbar tab and status area
    model_display_var = tk.StringVar(value=f"Model: {current_model_name.get()}")

    # Model selection and load button
    model_label = tk.Label(frame, text="Model:")
    model_label.pack(side=tk.LEFT, padx=(8, 2))
    model_choices = ["small", "medium", "large-v2"]
    model_combo = ttk.Combobox(frame, textvariable=current_model_name, values=model_choices, width=10, state="readonly")
    model_combo.pack(side=tk.LEFT)
    try:
        current_model_name.trace_add("write", _refresh_status_bar)
    except Exception:
        pass
    # Bind Enter key to trigger model load
    try:
        model_combo.bind("<Return>", lambda e: on_load_model())
    except Exception:
        pass

    loading_model = {"value": False}

    def on_load_model():
        if loading_model["value"]:
            return
        name = current_model_name.get().strip() or "small"
        loading_model["value"] = True
        set_status(f"Loading model: {name}…")
        def worker():
            nonlocal model
            try:
                new_model = load_whisper_model_with_retry(name)
                model = new_model
                set_status(f"Loaded model: {name}")
                try:
                    model_display_var.set(f"Model: {name}")
                except Exception:
                    pass
            except Exception as e:
                messagebox.showerror("Load Model Failed", str(e))
                # revert selection on failure
                try:
                    current_model_name.set("small")
                except Exception:
                    pass
            finally:
                loading_model["value"] = False
        threading.Thread(target=worker, daemon=True).start()

    load_model_btn = tk.Button(frame, text="Load", width=6, command=on_load_model)
    load_model_btn.pack(side=tk.LEFT, padx=(4, 0))

    # Stop/Break button to cancel batch loops
    stop_event = threading.Event()
    _current_ffmpeg_proc = {"proc": None}      # track running ffmpeg to terminate on Stop
    _current_transcribe_proc = {"proc": None}  # track running whisper subprocess to terminate on Stop
    def on_stop():
        stop_event.set()
        set_status("Stopping… will abort after current file.")
        try:
            transcribe_sel_btn.configure(text="Stopping…")
        except Exception:
            pass
        # Best-effort: terminate any active ffmpeg extraction
        try:
            p = _current_ffmpeg_proc.get("proc")
            if p and p.poll() is None:
                p.terminate()
        except Exception:
            pass
        # Terminate active transcription process immediately
        try:
            p2 = _current_transcribe_proc.get("proc")
            if p2 and p2.poll() is None:
                p2.terminate()
        except Exception:
            pass
    stop_btn = tk.Button(frame, text="Stop transcription", width=16, command=on_stop)
    stop_btn.pack(side=tk.LEFT, padx=(8, 0))

    # Language selector: Auto or pick a specific Whisper language
    language_label = tk.Label(frame, text="Language:")
    language_label.pack(side=tk.LEFT, padx=(8, 2))
    language_var = tk.StringVar(value="Auto")
    # Common Whisper-supported languages (label -> code)
    _LANG_OPTIONS = [
        ("Auto", None),
        ("English", "en"),
        ("Chinese", "zh"),
        ("Spanish", "es"),
        ("French", "fr"),
        ("German", "de"),
        ("Japanese", "ja"),
        ("Korean", "ko"),
        ("Portuguese", "pt"),
        ("Italian", "it"),
        ("Russian", "ru"),
        ("Hindi", "hi"),
        ("Arabic", "ar"),
        ("Dutch", "nl"),
        ("Turkish", "tr"),
        ("Polish", "pl"),
        ("Swedish", "sv"),
        ("Danish", "da"),
        ("Norwegian", "no"),
        ("Finnish", "fi"),
        ("Greek", "el"),
        ("Czech", "cs"),
        ("Ukrainian", "uk"),
        ("Vietnamese", "vi"),
        ("Thai", "th"),
        ("Indonesian", "id"),
        ("Malay", "ms"),
        ("Hebrew", "he"),
    ]
    language_labels = [lbl for (lbl, _) in _LANG_OPTIONS]
    language_combo = ttk.Combobox(frame, textvariable=language_var, values=language_labels, width=14, state="readonly")
    language_combo.pack(side=tk.LEFT)

    def _selected_language_code() -> str | None:
        try:
            sel = language_var.get()
            for lbl, code in _LANG_OPTIONS:
                if lbl == sel:
                    return code
        except Exception:
            pass
        return None

    # Accent bias (helps with Indian English pronunciation and terms)
    indian_bias_var = tk.BooleanVar(value=True)
    indian_bias_chk = tk.Checkbutton(frame, text="Indian English bias", variable=indian_bias_var)
    indian_bias_chk.pack(side=tk.LEFT, padx=(8, 0))

    # Stability Mode: enable beam search for steadier output (slower)
    stability_var = tk.BooleanVar(value=False)
    stability_chk = tk.Checkbutton(frame, text="Stability Mode (beam)", variable=stability_var)
    stability_chk.pack(side=tk.LEFT, padx=(8, 0))

    # Fast decode: greedy, temperature=0 (overrides Stability when ON)
    fast_decode_var = tk.BooleanVar(value=False)
    fast_decode_chk = tk.Checkbutton(frame, text="Fast Decode", variable=fast_decode_var)
    fast_decode_chk.pack(side=tk.LEFT, padx=(8, 0))

    # Repetition Guard: remove consecutive duplicate sentences in output
    repetition_guard_var = tk.BooleanVar(value=True)
    repetition_guard_chk = tk.Checkbutton(frame, text="Reduce repetition", variable=repetition_guard_var)
    repetition_guard_chk.pack(side=tk.LEFT, padx=(8, 0))

    # Stricter repetition guard
    strict_repetition_guard_var = tk.BooleanVar(value=True)
    strict_repetition_guard_chk = tk.Checkbutton(frame, text="Strict", variable=strict_repetition_guard_var)
    strict_repetition_guard_chk.pack(side=tk.LEFT, padx=(2, 0))

    def _selected_initial_prompt() -> str | None:
        # Provide an English bias prompt only when English is explicitly selected; augment for Indian English
        try:
            base = None
            if _selected_language_code() == 'en':
                base = "Transcribe the following English speech."
                if indian_bias_var.get():
                    base += " The speaker has an Indian English accent; prefer standard English words, keep technical terms as spoken, and avoid filling repeated phrases."
            return base
        except Exception:
            return None

    # Output mode selector
    output_label = tk.Label(frame, text="Output:")
    output_label.pack(side=tk.LEFT, padx=(8, 2))
    output_mode_var = tk.StringVar(value="Same Language")
    output_mode_combo = ttk.Combobox(
        frame,
        textvariable=output_mode_var,
        values=["Same Language", "English (Translate)", "Chinese (Translate)"],
        width=20,
        state="readonly",
    )
    output_mode_combo.pack(side=tk.LEFT)

    # Install translator on demand
    def ensure_deep_translator_installed() -> bool:
        try:
            import deep_translator  # noqa: F401
            return True
        except Exception:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "deep-translator"])  # lightweight Google Translate wrapper
                import deep_translator  # noqa: F401
                return True
            except Exception:
                append_log("Failed to install deep-translator; Chinese translation unavailable.")
                return False

    def translate_text(text: str, target_lang: str) -> str:
        try:
            from deep_translator import GoogleTranslator
            # Use auto source detection; target: 'zh-CN' for Chinese
            return GoogleTranslator(source='auto', target=target_lang).translate(text or "")
        except Exception as e:
            append_log(f"Translation failed: {e}")
            return text

    def compute_transcribe_args() -> dict:
        """Return kwargs for model.transcribe based on UI selections.
        Tuned to reduce repetitions and mis-detections.
        """
        lang = _selected_language_code()
        mode = output_mode_var.get()
        init_prompt = _selected_initial_prompt()

        # Base args: reduce variability + repetition
        args = dict(
            fp16=False,
            verbose=True,
            language=lang,
            task='transcribe',
            temperature=0,
            # If repetition guard is on, avoid using an initial prompt that might leak to output
            initial_prompt=(None if repetition_guard_var.get() else init_prompt),
            # repetition/garble safeguards
            condition_on_previous_text=False,
            compression_ratio_threshold=(1.8 if strict_repetition_guard_var.get() else 1.9),
            logprob_threshold=(-0.4 if strict_repetition_guard_var.get() else -0.2),
            no_speech_threshold=0.6,
        )

        # Beam search for stability when toggled (slower)
        if stability_var.get():
            args.update(beam_size=5, best_of=5)

        # Fast decode overrides beam search; enforce greedy
        if fast_decode_var.get():
            args['temperature'] = 0.0
            # Remove beam-related args if present
            try:
                args.pop('beam_size', None)
                args.pop('best_of', None)
            except Exception:
                pass

        # If we are specifically targeting English output, override to English
        if indian_bias_var.get() and (lang is None or lang != 'en'):
            # When biasing Indian English, force language to English if user hasn't explicitly chosen another
            args['language'] = 'en'

        if mode == "English (Translate)":
            # Whisper translate mode outputs English
            args.update(task='translate', language='en', initial_prompt=_selected_initial_prompt())
        elif mode == "Chinese (Translate)":
            # Keep task=transcribe in source language; we'll post-translate Chinese after
            pass
        return args

    # --- Real-time (incremental) transcription helpers ---
    def _fmt_time(seconds: float) -> str:
        try:
            seconds = int(max(0, round(seconds)))
            h, r = divmod(seconds, 3600)
            m, s = divmod(r, 60)
            if h > 0:
                return f"{h:d}:{m:02d}:{s:02d}"
            return f"{m:d}:{s:02d}"
        except Exception:
            return "0:00"

    def _state_path_for(input_path: str) -> str:
        try:
            folder = os.path.dirname(input_path)
            base = os.path.splitext(os.path.basename(input_path))[0]
            return os.path.join(folder, f"{base}.transcribe.state.json")
        except Exception:
            return os.path.join(tempfile.gettempdir(), "transcribe.state.json")

    def _resolve_ffmpeg_cmd() -> str:
        """Return the path to ffmpeg binary, checking PATH and common locations."""
        try:
            ffmpeg = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
            if ffmpeg:
                return ffmpeg
            # Fallback: try to find next to ffprobe
            probe = shutil.which("ffprobe") or shutil.which("ffprobe.exe")
            if probe:
                probe_dir = os.path.dirname(probe)
                if probe_dir:
                    for name in ("ffmpeg.exe", "ffmpeg"):
                        candidate = os.path.join(probe_dir, name)
                        if os.path.isfile(candidate):
                            return candidate
            return "ffmpeg"
        except Exception:
            return "ffmpeg"

    def _resolve_ffprobe_cmd() -> str:
        try:
            probe = shutil.which("ffprobe") or shutil.which("ffprobe.exe")
            if probe:
                return probe
            ffmpeg_bin = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
            if ffmpeg_bin:
                ffmpeg_dir = os.path.dirname(ffmpeg_bin)
                if ffmpeg_dir:
                    candidate = os.path.join(ffmpeg_dir, "ffprobe.exe")
                    if os.path.isfile(candidate):
                        return candidate
                    candidate = os.path.join(ffmpeg_dir, "ffprobe")
                    if os.path.isfile(candidate):
                        return candidate
            return "ffprobe"
        except Exception:
            return "ffprobe"

    def _probe_duration_seconds(path: str) -> float:
        """Probe media duration using ffprobe with multiple fallback strategies."""
        import json as _json
        probe_cmd = _resolve_ffprobe_cmd()
        
        # Strategy 1: Standard format duration probe
        try:
            cmd = [probe_cmd, "-v", "error", "-show_entries", "format=duration", "-of", "default=nk=1:nw=1", path]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if res.returncode == 0 and res.stdout.strip():
                dur = float(res.stdout.strip())
                if dur > 0:
                    return dur
        except Exception:
            pass
        
        # Strategy 2: JSON format probe (more robust for some files)
        try:
            cmd = [probe_cmd, "-v", "error", "-show_format", "-show_streams", "-of", "json", path]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if res.returncode == 0:
                data = _json.loads(res.stdout or "{}")
                # Try format duration first
                fmt = data.get("format", {})
                if "duration" in fmt and fmt["duration"]:
                    dur = float(fmt["duration"])
                    if dur > 0:
                        return dur
                # Fall back to first video/audio stream duration
                for stream in data.get("streams", []):
                    if "duration" in stream and stream["duration"]:
                        dur = float(stream["duration"])
                        if dur > 0:
                            return dur
        except Exception:
            pass
        
        # Strategy 3: Use ffmpeg to get duration (works for some files ffprobe can't handle)
        try:
            ffmpeg_cmd = _resolve_ffmpeg_cmd()
            cmd = [ffmpeg_cmd, "-i", path, "-f", "null", "-"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            # Parse duration from stderr output
            import re
            dur_match = re.search(r"Duration:\s+(\d+):(\d+):(\d+\.?\d*)", res.stderr)
            if dur_match:
                h, m, s = map(float, dur_match.groups())
                dur = h * 3600 + m * 60 + s
                if dur > 0:
                    return dur
        except Exception:
            pass
        
        return 0.0

    def _probe_audio_streams(input_path: str) -> list:
        """Return a list of audio stream metadata using ffprobe. Each item includes
        position (0-based among audio streams), index, channels, bitrate, language, codec_name.
        """
        try:
            import json as _json
            # Prefer ffprobe; if missing, try ffprobe.exe explicitly (Windows)
            probe_cmd = _resolve_ffprobe_cmd()
            cmd = [
                probe_cmd, "-v", "error",
                "-select_streams", "a",
                "-show_entries", "stream=index,channels,codec_name,channel_layout,bit_rate:stream_tags=language",
                "-of", "json",
                input_path,
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                try:
                    append_log(f"ffprobe failed (code {res.returncode}). Streams unavailable.\n{res.stderr[:400] if res.stderr else ''}")
                except Exception:
                    pass
                return []
            data = _json.loads(res.stdout or "{}")
            streams = data.get("streams", [])
            items = []
            for pos, s in enumerate(streams):
                try:
                    items.append({
                        "pos": pos,
                        "index": int(s.get("index", pos)),
                        "channels": int(s.get("channels", 0) or 0),
                        "bit_rate": int(s.get("bit_rate", 0) or 0),
                        "language": str((s.get("tags", {}) or {}).get("language", "")).lower(),
                        "codec_name": s.get("codec_name", ""),
                    })
                except Exception:
                    pass
            # Prefer more channels, then higher bitrate, prefer english/und
            def _lang_rank(lang: str) -> int:
                if lang in ("eng", "en", ""): return 2
                if lang in ("und", "undetermined"): return 1
                return 0
            items.sort(key=lambda x: (x.get("channels", 0), x.get("bit_rate", 0), _lang_rank(x.get("language", ""))), reverse=True)
            return items
        except FileNotFoundError:
            try:
                append_log("ffprobe not found on PATH. Stream dropdown will show only 'Auto'.")
            except Exception:
                pass
            return []
        except Exception as e:
            try:
                append_log(f"Stream probe error: {e}")
            except Exception:
                pass
            return []

    def _extract_time_clip(input_path: str, start_sec: float, dur_sec: float, out_wav: str) -> bool:
        """Use ffmpeg to extract a PCM WAV clip [start, start+dur)."""
        try:
            os.makedirs(os.path.dirname(out_wav) or tempfile.gettempdir(), exist_ok=True)
        except Exception:
            pass
        ffmpeg_cmd = _resolve_ffmpeg_cmd()
        cmd = [
            ffmpeg_cmd, "-y", "-ss", str(max(0, start_sec)), "-i", input_path,
            "-t", str(max(0.1, dur_sec)),
            "-vn", "-ac", "2", "-ar", "16000", "-acodec", "pcm_s16le",
            out_wav,
        ]
        try:
            # Capture stderr for diagnostics instead of hiding it
            p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
            _current_ffmpeg_proc["proc"] = p
            stderr_output = ""
            while True:
                if stop_event.is_set():
                    try:
                        p.terminate()
                    except Exception:
                        pass
                    return False
                rc = p.poll()
                if rc is None:
                    root.update_idletasks(); root.update()
                    continue
                # Process finished, collect any remaining stderr
                try:
                    _, err = p.communicate(timeout=1)
                    if err:
                        stderr_output += err
                except Exception:
                    pass
                break
            _current_ffmpeg_proc["proc"] = None
            if rc != 0 and stderr_output:
                try:
                    append_log(f"ffmpeg extraction error: {stderr_output[:500]}")
                except Exception:
                    pass
            return rc == 0 and os.path.isfile(out_wav)
        except FileNotFoundError as e:
            try:
                append_log(f"ffmpeg not found: {e}. Ensure FFmpeg is installed and on PATH.")
            except Exception:
                pass
            _current_ffmpeg_proc["proc"] = None
            return False
        except Exception as e:
            try:
                append_log(f"ffmpeg extraction failed: {e}")
            except Exception:
                pass
            _current_ffmpeg_proc["proc"] = None
            return False

    def _dedupe_consecutive_sentences(text: str, max_repeat: int = 1) -> str:
        """Collapse consecutive identical sentences. Keeps up to max_repeat copies.
        Sentence split is heuristic using punctuation. Whitespace-normalized compare.
        """
        try:
            import re
            sents = re.split(r"([.!?]\s+)", text.strip())
            if not sents:
                return text
            # Re-join using captured delimiters; build logical sentences
            logical = []
            i = 0
            cur = ""
            while i < len(sents):
                chunk = sents[i]
                if i + 1 < len(sents) and re.match(r"[.!?]\s+", sents[i+1] or ""):
                    cur = (chunk or "") + (sents[i+1] or "")
                    i += 2
                else:
                    cur = chunk
                    i += 1
                if cur:
                    logical.append(cur)
            out = []
            last = None
            cnt = 0
            for sen in logical:
                key = " ".join(sen.split()).lower()
                if last is not None and key == last:
                    if cnt < max_repeat:
                        out.append(sen)
                        cnt += 1
                else:
                    out.append(sen)
                    last = key
                    cnt = 0
            return "".join(out)
        except Exception:
            return text

    def _split_sentences(text: str) -> list:
        """Heuristic sentence splitter used for cross-chunk de-duplication."""
        try:
            import re
            parts = re.split(r"([.!?]\s+)", text.strip())
            if not parts:
                return []
            sents = []
            i = 0
            while i < len(parts):
                chunk = parts[i]
                if i + 1 < len(parts) and re.match(r"[.!?]\s+", parts[i+1] or ""):
                    sents.append((chunk or "") + (parts[i+1] or ""))
                    i += 2
                else:
                    if chunk:
                        sents.append(chunk)
                    i += 1
            return sents
        except Exception:
            return [text]

    def _post_process_dedupe_file(file_path: str):
        """Read a file, globally de-duplicate consecutive sentences, and overwrite."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            if not content.strip():
                return
            deduped = _dedupe_consecutive_sentences(content, max_repeat=0)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(deduped)
        except Exception as e:
            append_log(f"Post-process dedupe failed: {e}")

    def _strip_initial_prompt_leak(text: str, prompt: str | None) -> str:
        """Remove occurrences of the initial prompt text if Whisper echoes it.
        Uses case-insensitive whitespace-normalized matching; strips leading and repeated lines.
        """
        try:
            if not text or not prompt:
                return text
            key = " ".join((prompt or "").split()).lower()
            if not key:
                return text
            import re
            # Remove at beginning
            def norm(s: str) -> str:
                return " ".join((s or "").split()).lower()
            t = text
            # Drop repeated full-line echoes
            lines = [ln for ln in t.splitlines() if norm(ln) != key]
            t = "\n".join(lines)
            # Drop leading occurrence without newline boundaries
            while norm(t).startswith(key):
                t = t[len(t):] if False else re.sub(r"^\s*" + re.escape(prompt) + r"\s*", "", t, flags=re.IGNORECASE)
                break
            # Also remove standalone sentence occurrences
            t = re.sub(re.escape(prompt), "", t, flags=re.IGNORECASE)
            return t.strip()
        except Exception:
            return text

    def transcribe_incremental(input_path: str, output_txt: str, chunk_sec: int = 60, resume: bool = True):
        """Transcribe in chunks and append to output file as we go.
        Respects Stop button between chunks. Uses in-process Whisper model for speed.
        """
        total = _probe_duration_seconds(input_path)
        if total <= 0:
            # ffprobe couldn't read duration (possibly corrupt container or unsupported). Try explicit audio extraction first.
            try:
                try:
                    append_log("Media duration is 0s or unreadable. Attempting audio extraction to WAV…")
                except Exception:
                    pass
                tmp_wav = os.path.join(tempfile.gettempdir(), f"whisper_fallback_{os.getpid()}.wav")
                # Respect user-selected stream if any
                try:
                    forced_pos = _selected_audio_stream_pos()
                except Exception:
                    forced_pos = None
                ok = extract_audio_to_wav(input_path, tmp_wav, force_pos=forced_pos)
                if (not ok) or (not os.path.isfile(tmp_wav)):
                    try:
                        ext = os.path.splitext(input_path)[1] or ".mp4"
                        remux_tmp = os.path.join(
                            tempfile.gettempdir(),
                            f"whisper_remux_{os.getpid()}_{int(datetime.now().timestamp())}{ext}",
                        )
                        append_log("Media unreadable. Attempting remux repair and retry…")
                        remux_ok = remux_media(input_path, remux_tmp)
                        if remux_ok and os.path.isfile(remux_tmp):
                            append_log(f"Remux successful → {os.path.basename(remux_tmp)}. Retrying extraction…")
                            ok = extract_audio_to_wav(remux_tmp, tmp_wav, force_pos=forced_pos)
                    except Exception:
                        pass
                    finally:
                        try:
                            if 'remux_tmp' in locals() and os.path.isfile(remux_tmp):
                                os.remove(remux_tmp)
                        except Exception:
                            pass
                if ok and os.path.isfile(tmp_wav):
                    args = compute_transcribe_args()
                    result = model.transcribe(tmp_wav, **args)
                    text = result.get("text", "").strip()
                    if output_mode_var.get() == "Chinese (Translate)" and text:
                        if ensure_deep_translator_installed():
                            text = translate_text(text, target_lang='zh-CN')
                    with open(output_txt, "w", encoding="utf-8") as f:
                        f.write(text)
                    return
                # Extraction failed; provide actionable guidance and abort gracefully
                try:
                    sz = os.path.getsize(input_path) if os.path.exists(input_path) else 0
                except Exception:
                    sz = 0
                try:
                    append_log(
                        "FFmpeg/ffprobe could not read this media (duration=0). The file may be incomplete or missing the 'moov' atom.\n"
                        f"Path: {input_path}\n"
                        f"Size: {sz} bytes\n"
                        "Suggestions: re-download the file, or try another source. If it's a valid MP4 but has metadata issues, remux with a tool and retry."
                    )
                except Exception:
                    pass
                raise RuntimeError("Unreadable media: ffmpeg could not extract audio. Skipping.")
            finally:
                # Best-effort cleanup of temp file; ignore errors
                try:
                    if 'tmp_wav' in locals() and os.path.isfile(tmp_wav):
                        os.remove(tmp_wav)
                except Exception:
                    pass

        # Prepare file
        start = 0.0
        state_path = _state_path_for(input_path)
        state = None
        if resume:
            try:
                if os.path.isfile(state_path):
                    with open(state_path, "r", encoding="utf-8", errors="replace") as sf:
                        state = json.load(sf)
                # Validate state belongs to this file (by path and total duration within 2s)
                if state and state.get("source") == os.path.abspath(input_path):
                    if abs(float(state.get("total", 0.0)) - float(total)) <= 2.0:
                        start = float(state.get("last_end", 0.0))
            except Exception:
                state = None

        # If not resuming or first time, truncate file. If resuming, keep and append.
        if not (resume and state and start > 0.01 and os.path.isfile(output_txt)):
            try:
                with open(output_txt, "w", encoding="utf-8") as f:
                    f.write("")
            except Exception:
                pass

        idx = 1
        # Initial progress status
        try:
            pct0 = int((min(total, start) / max(0.01, total)) * 100)
            set_status(f"{pct0}% ({_fmt_time(start)} / {_fmt_time(total)})")
        except Exception:
            pass
        # Create/refresh state file immediately so resume is possible even if stopped early
        try:
            with open(state_path, "w", encoding="utf-8") as sf:
                json.dump({
                    "source": os.path.abspath(input_path),
                    "total": float(total),
                    "chunk_sec": int(chunk_sec),
                    "last_end": float(start),
                    "updated": datetime.now().isoformat(timespec='seconds'),
                }, sf)
        except Exception:
            pass
        from collections import deque
        prev_tail_key = None  # rolling de-dup across chunk boundaries
        # Use a larger memory window in strict mode
        recent_keys = deque(maxlen=(24 if strict_repetition_guard_var.get() else 12))
        while start < total - 0.01:
            if stop_event.is_set():
                # Persist state at current boundary before exiting
                try:
                    with open(state_path, "w", encoding="utf-8") as sf:
                        json.dump({
                            "source": os.path.abspath(input_path),
                            "total": float(total),
                            "chunk_sec": int(chunk_sec),
                            "last_end": float(start),
                            "updated": datetime.now().isoformat(timespec='seconds'),
                        }, sf)
                except Exception:
                    pass
                break
            cur = min(chunk_sec, max(0.5, total - start))
            tmp_wav = os.path.join(tempfile.gettempdir(), f"whisper_chunk_{os.getpid()}_{idx}.wav")
            ok = _extract_time_clip(input_path, start, cur, tmp_wav)
            if not ok:
                append_log(f"Chunk {idx}: failed to extract audio segment at {start:.0f}s")
                break
            try:
                args = compute_transcribe_args()
                # Use greedy for speed in chunks if Fast Decode enabled
                result = model.transcribe(tmp_wav, **args)
                piece = result.get("text", "").strip()
                # Strip any leaked initial prompt
                try:
                    piece = _strip_initial_prompt_leak(piece, _selected_initial_prompt())
                except Exception:
                    pass
                if repetition_guard_var.get() and piece:
                    # Intra-chunk de-dup
                    piece = _dedupe_consecutive_sentences(piece, max_repeat=0)
                    # Cross-chunk boundary de-dup (drop leading sentences that match previous tail)
                    sents = _split_sentences(piece)
                    if sents and prev_tail_key is not None:
                        def _key(s: str) -> str:
                            return " ".join((s or "").split()).lower()
                        # Drop leading duplicates
                        k = _key(sents[0])
                        j = 0
                        while j < len(sents) and _key(sents[j]) == prev_tail_key:
                            j += 1
                        if j > 0:
                            piece = "".join(sents[j:])
                            sents = sents[j:]
                    # Rolling-window suppression: drop sentences that already appeared recently
                    if sents:
                        def _key(s: str) -> str:
                            return " ".join((s or "").split()).lower()
                        filtered = []
                        for sen in sents:
                            k = _key(sen)
                            if k and k in recent_keys:
                                # skip repeated looped line
                                continue
                            filtered.append(sen)
                            if k:
                                recent_keys.append(k)
                        piece = "".join(filtered)
                if output_mode_var.get() == "Chinese (Translate)" and piece:
                    if ensure_deep_translator_installed():
                        piece = translate_text(piece, target_lang='zh-CN')
                with open(output_txt, "a", encoding="utf-8") as f:
                    if (start > 0 or (resume and state and os.path.getsize(output_txt) > 0)) and piece and not piece.startswith(" "):
                        f.write(" ")
                    f.write(piece)
                    f.flush()
                # Update rolling tail key
                if repetition_guard_var.get():
                    s_tail = _split_sentences(piece)
                    if s_tail:
                        prev_tail_key = " ".join(s_tail[-1].split()).lower()
                # Update UI preview + progress
                try:
                    out_norm = _normpath(output_txt)
                    output_path_var.set(out_norm)
                    done = min(total, start + cur)
                    pct = int((done / max(0.01, total)) * 100)
                    set_status(f"{pct}% ({_fmt_time(done)} / {_fmt_time(total)})")
                except Exception:
                    pass
                # Persist resume state after each successful chunk
                try:
                    with open(state_path, "w", encoding="utf-8") as sf:
                        json.dump({
                            "source": os.path.abspath(input_path),
                            "total": float(total),
                            "chunk_sec": int(chunk_sec),
                            "last_end": float(min(total, start + cur)),
                            "updated": datetime.now().isoformat(timespec='seconds'),
                        }, sf)
                except Exception:
                    pass
            except Exception as e:
                append_log(f"Chunk {idx} error: {e}")
                append_log(traceback.format_exc())
                break
            finally:
                try:
                    if os.path.isfile(tmp_wav):
                        os.remove(tmp_wav)
                except Exception:
                    pass
            start += cur
            idx += 1
        # Final 100% status if completed (and not canceled)
        if not stop_event.is_set():
            try:
                set_status(f"100% ({_fmt_time(total)} / {_fmt_time(total)})")
            except Exception:
                pass
            # Remove state file on successful completion
            try:
                if os.path.isfile(state_path):
                    os.remove(state_path)
            except Exception:
                pass
            # Final de-dupe pass on the whole file
            if repetition_guard_var.get():
                try:
                    _post_process_dedupe_file(output_txt)
                except Exception:
                    pass

    def _build_whisper_cli_cmd(input_path: str, out_dir: str, model_name: str, args: dict) -> list[str]:
        """Translate our UI args into a `python -m whisper` CLI invocation.
        We keep options aligned where possible and favor safety over completeness.
        """
        cmd = [sys.executable, "-m", "whisper", input_path, "--model", model_name, "--output_dir", out_dir]
        # fp16
        try:
            if not args.get("fp16", False):
                cmd += ["--fp16", "False"]
        except Exception:
            pass
        # verbose
        try:
            cmd += ["--verbose", "True" if args.get("verbose", False) else "False"]
        except Exception:
            pass
        # language
        try:
            if args.get("language"):
                cmd += ["--language", str(args["language"]) ]
        except Exception:
            pass
        # task
        try:
            if args.get("task") == "translate":
                cmd += ["--task", "translate"]
            else:
                cmd += ["--task", "transcribe"]
        except Exception:
            pass
        # temperature
        try:
            cmd += ["--temperature", str(args.get("temperature", 0))]
        except Exception:
            pass
        # beam settings
        try:
            if "beam_size" in args:
                cmd += ["--beam_size", str(args["beam_size"]) ]
            if "best_of" in args:
                cmd += ["--best_of", str(args["best_of"]) ]
        except Exception:
            pass
        # initial prompt (if provided)
        try:
            if args.get("initial_prompt"):
                cmd += ["--initial_prompt", str(args["initial_prompt"]) ]
        except Exception:
            pass
        return cmd

    def _find_latest_txt_for_base(out_dir: str, base: str) -> str | None:
        try:
            candidates = []
            for name in os.listdir(out_dir):
                if not name.lower().endswith(".txt"):
                    continue
                if not name.startswith(base):
                    # Whisper CLI often produces base or base.<lang>.txt; allow startswith
                    continue
                full = os.path.join(out_dir, name)
                try:
                    ts = os.path.getmtime(full)
                except Exception:
                    ts = 0
                candidates.append((ts, full))
            if not candidates:
                return None
            candidates.sort(reverse=True)
            return candidates[0][1]
        except Exception:
            return None

    def transcribe_with_cli(input_path: str, model_name: str, args: dict) -> tuple[str, str | None]:
        """Run Whisper in a subprocess so we can stop mid-file.
        Returns (transcript_text, output_file_path or None).
        """
        out_dir = os.path.dirname(input_path) or os.getcwd()
        base = os.path.splitext(os.path.basename(input_path))[0]
        cmd = _build_whisper_cli_cmd(input_path, out_dir, model_name, args)
        try:
            p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            _current_transcribe_proc["proc"] = p
            while True:
                if stop_event.is_set():
                    try:
                        p.terminate()
                    except Exception:
                        pass
                    _current_transcribe_proc["proc"] = None
                    raise RuntimeError("Transcription canceled by user.")
                rc = p.poll()
                if rc is None:
                    root.update_idletasks(); root.update()
                    continue
                break
            _current_transcribe_proc["proc"] = None
            if rc != 0:
                raise RuntimeError("Whisper CLI failed.")
            # locate output txt
            out_txt = _find_latest_txt_for_base(out_dir, base)
            text = ""
            if out_txt and os.path.isfile(out_txt):
                with open(out_txt, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read().strip()
            return text, out_txt
        except Exception as e:
            _current_transcribe_proc["proc"] = None
            raise

    # Recent folders: dropdown with auto-fit width and +/- adjusters + open button
    recent_label = tk.Label(frame, text="Recent:")
    recent_label.pack(side=tk.LEFT, padx=(8, 4))
    recent_var = tk.StringVar(value="")
    recent_width_var = tk.IntVar(value=30)
    recent_combo = ttk.Combobox(frame, textvariable=recent_var, width=recent_width_var.get(), state="readonly")
    recent_combo.pack(side=tk.LEFT, padx=(0, 4))
    # Change selection -> switch file list
    try:
        recent_combo.bind("<<ComboboxSelected>>", lambda e: open_recent_selected())
    except Exception:
        pass

    def update_recent_combo_width(candidates: list[str] | None = None):
        try:
            # Choose primary widget (prefer the toolbar tab combobox if available)
            try:
                target_widget = recent_combo_tab  # defined later; safe if exists
            except Exception:
                target_widget = recent_combo
            # Determine the longest string width in pixels based on the chosen widget
            font_obj = tkfont.nametofont(str(target_widget.cget("font"))) if target_widget.cget("font") else tkfont.nametofont("TkDefaultFont")
        except Exception:
            font_obj = tkfont.nametofont("TkDefaultFont")
        try:
            # Use provided candidates, otherwise read from whichever widget currently holds values
            if candidates is not None:
                vals = candidates
            else:
                try:
                    vals = list(recent_combo_tab["values"]) if recent_combo_tab["values"] else []
                except Exception:
                    vals = list(recent_combo["values"]) if recent_combo["values"] else []
        except Exception:
            vals = []
        samples = [str(v) for v in vals if v]
        cur = recent_var.get()
        if cur:
            samples.append(str(cur))
        try:
            max_px = max([font_obj.measure(s) for s in samples], default=0)
        except Exception:
            max_px = 0
        try:
            avg_px = font_obj.measure("0") or 7
        except Exception:
            avg_px = 7
        # Convert pixels to approximate character width, add padding
        width_chars = int(math.ceil((max_px + 24) / max(1, avg_px)))
        width_chars = max(20, min(100, width_chars))
        try:
            recent_width_var.set(width_chars)
            # Apply to both widgets if present
            try:
                recent_combo_tab.configure(width=width_chars)
            except Exception:
                pass
            try:
                recent_combo.configure(width=width_chars)
            except Exception:
                pass
        except Exception:
            pass

    def adjust_recent_width(delta: int):
        try:
            w = int(recent_width_var.get()) + int(delta)
        except Exception:
            w = 30
        w = max(10, min(120, w))
        recent_width_var.set(w)
        try:
            recent_combo.configure(width=w)
        except Exception:
            pass

    # Provide small -/+ buttons to adjust combobox width
    dec_btn = tk.Button(frame, text="−", width=2, command=lambda: adjust_recent_width(-4))
    inc_btn = tk.Button(frame, text="+", width=2, command=lambda: adjust_recent_width(+4))
    dec_btn.pack(side=tk.LEFT, padx=(0, 2))
    inc_btn.pack(side=tk.LEFT, padx=(0, 6))

    # Double-click the combobox to auto-fit to current values
    try:
        recent_combo.bind("<Double-Button-1>", lambda e: update_recent_combo_width(None))
    except Exception:
        pass

    recent_open_btn = tk.Button(frame, text="Open", width=6)
    recent_open_btn.pack(side=tk.LEFT)

    # --- Grouped Toolbar (Notebook) ---
    # Create a tabbed toolbar for better organization: Model | Options | Folders
    toolbar_nb = ttk.Notebook(root)
    toolbar_nb.pack(fill=tk.X, padx=8, pady=(6, 2))

    # Model tab
    tab_model = tk.Frame(toolbar_nb)
    toolbar_nb.add(tab_model, text="Model")
    tk.Label(tab_model, text="Model:").pack(side=tk.LEFT, padx=(4, 2))
    model_combo_tab = ttk.Combobox(tab_model, textvariable=current_model_name, values=["small", "medium", "large-v2"], width=12, state="readonly")
    model_combo_tab.pack(side=tk.LEFT)
    try:
        model_combo_tab.bind("<Return>", lambda e: on_load_model())
    except Exception:
        pass
    tk.Button(tab_model, text="Load", width=8, command=on_load_model).pack(side=tk.LEFT, padx=(6, 2))
    # Show current model on the right side of the tab
    tk.Label(tab_model, textvariable=model_display_var, fg="#666").pack(side=tk.RIGHT, padx=(2, 4))

    # Folders tab
    tab_folders = tk.Frame(toolbar_nb)
    toolbar_nb.add(tab_folders, text="Folders")
    tk.Label(tab_folders, text="Recent:").pack(side=tk.LEFT, padx=(4, 4))
    recent_combo_tab = ttk.Combobox(tab_folders, textvariable=recent_var, width=recent_width_var.get(), state="readonly")
    recent_combo_tab.pack(side=tk.LEFT, padx=(0, 4))
    # Change selection in tab -> switch file list
    try:
        recent_combo_tab.bind("<<ComboboxSelected>>", lambda e: open_recent_selected())
    except Exception:
        pass
    # Bind double-click to auto-fit
    try:
        recent_combo_tab.bind("<Double-Button-1>", lambda e: update_recent_combo_width(None))
    except Exception:
        pass
    # Width adjusters
    tk.Button(tab_folders, text="−", width=2, command=lambda: adjust_recent_width(-4)).pack(side=tk.LEFT, padx=(0, 2))
    tk.Button(tab_folders, text="+", width=2, command=lambda: adjust_recent_width(+4)).pack(side=tk.LEFT, padx=(0, 6))
    tk.Button(tab_folders, text="Open", width=8, command=lambda: open_recent_selected()).pack(side=tk.LEFT)
    
    # Options tab
    tab_options = tk.Frame(toolbar_nb)
    toolbar_nb.add(tab_options, text="Options")
    tk.Label(tab_options, text="Language:").pack(side=tk.LEFT, padx=(4, 2))
    language_combo_tab = ttk.Combobox(tab_options, textvariable=language_var, values=[lbl for (lbl, _) in _LANG_OPTIONS], width=16, state="readonly")
    language_combo_tab.pack(side=tk.LEFT)
    tk.Checkbutton(tab_options, text="Indian English bias", variable=indian_bias_var).pack(side=tk.LEFT, padx=(8, 0))
    tk.Checkbutton(tab_options, text="Stability Mode (beam)", variable=stability_var).pack(side=tk.LEFT, padx=(8, 0))
    tk.Checkbutton(tab_options, text="Fast Decode", variable=fast_decode_var).pack(side=tk.LEFT, padx=(8, 0))
    tk.Label(tab_options, text="Output:").pack(side=tk.LEFT, padx=(12, 2))
    output_mode_combo_tab = ttk.Combobox(
        tab_options,
        textvariable=output_mode_var,
        values=["Same Language", "English (Translate)", "Chinese (Translate)"],
        width=22,
        state="readonly",
    )
    output_mode_combo_tab.pack(side=tk.LEFT)

    # V2A tab in the toolbar notebook: Extract/Remux/Stream controls
    tab_v2a = tk.Frame(toolbar_nb)
    toolbar_nb.add(tab_v2a, text="V2A")
    v2a_toolbar = tk.Frame(tab_v2a)
    v2a_toolbar.pack(fill=tk.X, padx=8, pady=(6, 6))
    # Buttons wired to the original hidden controls
    tk.Button(v2a_toolbar, text="Extract Audio Only", width=18, command=lambda: extract_only_btn.invoke()).pack(side=tk.LEFT)
    tk.Button(v2a_toolbar, text="Remux Selected", width=16, command=lambda: remux_btn.invoke()).pack(side=tk.LEFT, padx=(6, 0))
    tk.Label(v2a_toolbar, text="Stream:").pack(side=tk.LEFT, padx=(8, 2))
    audio_stream_combo_v2a = ttk.Combobox(v2a_toolbar, textvariable=audio_stream_choice_var, values=["Auto"], width=28, state="readonly")
    audio_stream_combo_v2a.pack(side=tk.LEFT)
    tk.Button(v2a_toolbar, text="Refresh Streams", width=16, command=lambda: refresh_streams_btn.invoke()).pack(side=tk.LEFT, padx=(6, 0))
    tk.Button(v2a_toolbar, text="Preview Stream", width=16, command=lambda: preview_stream_btn.invoke()).pack(side=tk.LEFT, padx=(6, 0))
    tk.Button(v2a_toolbar, text="Transcribe Extracted", width=18, command=lambda: transcribe_extracted_btn.invoke()).pack(side=tk.LEFT, padx=(6, 0))

    # Filter tab: real-time filter by file name and by content in .txt/.md
    tab_filter = tk.Frame(toolbar_nb)
    toolbar_nb.add(tab_filter, text="Filter")
    current_filter_var = tk.StringVar(value="")
    tk.Label(tab_filter, text="Name contains:").pack(side=tk.LEFT, padx=(6, 4))
    filter_entry = ttk.Entry(tab_filter, textvariable=current_filter_var, width=36)
    filter_entry.pack(side=tk.LEFT, padx=(0, 6))
    clear_btn = tk.Button(tab_filter, text="Clear", width=8, command=lambda: (current_filter_var.set("")))
    clear_btn.pack(side=tk.LEFT)
    # Content filter UI
    content_filter_var = tk.StringVar(value="")
    tk.Label(tab_filter, text="Content contains:").pack(side=tk.LEFT, padx=(16, 4))
    content_entry = ttk.Entry(tab_filter, textvariable=content_filter_var, width=36)
    content_entry.pack(side=tk.LEFT, padx=(0, 6))
    clear_content_btn = tk.Button(tab_filter, text="Clear", width=8, command=lambda: (content_filter_var.set("")))
    clear_content_btn.pack(side=tk.LEFT)

    # Hide legacy inline controls to declutter original single-row toolbar
    try:
        # Model controls
        model_label.pack_forget()
        model_combo.pack_forget()
        load_model_btn.pack_forget()
    except Exception:
        pass
    try:
        # Language and output controls
        language_label.pack_forget()
        indian_bias_chk.pack_forget()
        stability_chk.pack_forget()
        fast_decode_chk.pack_forget()
        language_combo.pack_forget()
        output_label.pack_forget()
        output_mode_combo.pack_forget()
    except Exception:
        pass
    try:
        # Recent controls and width buttons
        recent_label.pack_forget()
        recent_combo.pack_forget()
        dec_btn.pack_forget(); inc_btn.pack_forget(); recent_open_btn.pack_forget()
    except Exception:
        pass

    # Auto-fit soon after layout (after values may have been populated)
    try:
        root.after(300, lambda: update_recent_combo_width(None))
    except Exception:
        pass

    quit_btn = tk.Button(frame, text="Quit", command=root.destroy)
    quit_btn.pack(side=tk.RIGHT)

    # Files pane show/hide toggle
    files_toggle_btn = tk.Button(frame, text="Files ▼")
    files_toggle_btn.pack(side=tk.RIGHT, padx=(6, 0))

    # Single status bar label (file + status + model + legend)
    status_bar_label = tk.Label(root, textvariable=status_bar_var, anchor="w")
    status_bar_label.pack(fill=tk.X, padx=8, pady=(4, 6))
    _refresh_status_bar()

    # Paned layout: upper file list, lower log
    paned = ttk.Panedwindow(root, orient=tk.VERTICAL)
    paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 6))

    # Upper: file browser tree
    files_frame = tk.Frame(paned)
    cols = ("audio", "size", "modified", "transcript", "txt_size", "md_size")
    tree = ttk.Treeview(files_frame, columns=cols, show="headings", height=6, selectmode="extended")
    header_labels = {
        "audio": "Audio/Video File",
        "size": "Size",
        "modified": "Date Modified",
        "transcript": "Transcript .txt",
        "txt_size": "TXT Size",
        "md_size": "MD Size",
    }
    tree.heading("audio", text=header_labels["audio"], command=lambda c="audio": tree_sort_by(c), anchor="w")
    tree.heading("size", text=header_labels["size"], command=lambda c="size": tree_sort_by(c), anchor="center")
    tree.heading("modified", text=header_labels["modified"], command=lambda c="modified": tree_sort_by(c), anchor="center")
    tree.heading("transcript", text=header_labels["transcript"], command=lambda c="transcript": tree_sort_by(c), anchor="center")
    tree.heading("txt_size", text=header_labels["txt_size"], command=lambda c="txt_size": tree_sort_by(c), anchor="center")
    tree.heading("md_size", text=header_labels["md_size"], command=lambda c="md_size": tree_sort_by(c), anchor="center")
    tree.column("audio", width=360, anchor="w")
    tree.column("size", width=90, anchor="center")
    tree.column("modified", width=160, anchor="center")
    tree.column("transcript", width=260, anchor="center")
    tree.column("txt_size", width=90, anchor="center")
    tree.column("md_size", width=90, anchor="center")
    # Legend moved into the consolidated status bar above
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    tree_scroll = ttk.Scrollbar(files_frame, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=tree_scroll.set)
    tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    paned.add(files_frame, weight=0)

    # Maintain a master list of all entries to enable filtering without re-scanning disk
    all_entries = []  # list of tuples: (audio_name, full_audio_path, size_str, modified_str, transcript, has_audio, txt_size_b, md_size_b)

    def _entry_matches_filter(entry: tuple, tokens: list[str]) -> bool:
        """Name filter: treat spaces as AND. Each token must appear in either the
        display name or the transcript base name."""
        try:
            if not tokens:
                return True
            name = str(entry[0] or "").lower()
            transcript_path = str(entry[4] or "").lower() if len(entry) > 4 else ""
            try:
                base_txt = (os.path.basename(transcript_path) or "").lower()
            except Exception:
                base_txt = (transcript_path or "").lower()
            for tok in tokens:
                if not tok:
                    continue
                if tok not in name and tok not in base_txt:
                    return False
            return True
        except Exception:
            return True

    # Cache for content searches; key by (path, token) to reuse across queries
    _content_cache = {"map": {}}  # map: (path, token) -> bool

    def _candidate_md_paths_for_entry(entry: tuple) -> list:
        # Prefer transcript-based md path; also try audio-based md path in current folder
        paths = []
        try:
            vals_transcript = entry[4] if len(entry) > 4 else ""
            txt_path = vals_transcript if isinstance(vals_transcript, str) else ""
            if txt_path:
                try:
                    mdp = md_path_for_transcript(txt_path)
                    if mdp:
                        paths.append(mdp)
                except Exception:
                    pass
            # Audio-based from display name
            audio_display = str(entry[0] or "")
            if audio_display.startswith("🎥 "):
                audio_display = audio_display[2:].lstrip()
            base_name = audio_display.replace(" (md only)", "").replace(" (no audio)", "").strip()
            try:
                base_name = os.path.splitext(base_name)[0]
            except Exception:
                pass
            folder = (current_folder_var.get() or "").strip()
            if folder and base_name:
                paths.append(os.path.join(folder, base_name + ".md"))
        except Exception:
            pass
        # Dedup while preserving order
        out = []
        seen = set()
        for p in paths:
            if p and p not in seen:
                out.append(p); seen.add(p)
        return out

    def _file_contains(path: str, token: str) -> bool:
        try:
            if not path or not os.path.isfile(path):
                return False
            m = _content_cache["map"]
            key = (path, token)
            if key in m:
                return m[key]
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                # Limit read to avoid huge memory; read up to 2 MB
                content = f.read(2 * 1024 * 1024)
            found = (token in (content or "").lower())
            m[key] = found
            return found
        except Exception:
            return False

    def _entry_content_contains(entry: tuple, tokens: list[str]) -> bool:
        """Content filter: treat spaces as AND. Each token must be present in
        either the .txt or one of the candidate .md files for that entry.
        Tokens may be satisfied across different files."""
        if not tokens:
            return True
        # Determine candidate files once
        try:
            txt_path = str(entry[4]) if len(entry) > 4 else ""
        except Exception:
            txt_path = ""
        md_candidates = _candidate_md_paths_for_entry(entry)
        for tok in tokens:
            if not tok:
                continue
            t = tok.lower()
            satisfied = False
            # Check transcript
            if isinstance(txt_path, str) and txt_path and txt_path != "(missing)":
                if _file_contains(txt_path, t):
                    satisfied = True
            # Check md files if not yet satisfied
            if not satisfied:
                for mdp in md_candidates:
                    if _file_contains(mdp, t):
                        satisfied = True
                        break
            if not satisfied:
                return False
        return True

    def apply_filter():
        # Rebuild the visible rows based on current filter
        try:
            name_q = (current_filter_var.get() or "").strip().lower()
        except Exception:
            name_q = ""
        try:
            content_q = (content_filter_var.get() or "").strip()
        except Exception:
            content_q = ""
        # Tokenize queries (space-separated AND)
        name_tokens = [t for t in name_q.split() if t]
        content_tokens = [t for t in content_q.split() if t]
        # Clear existing rows
        try:
            for iid in tree.get_children():
                tree.delete(iid)
        except Exception:
            pass
        path_to_item.clear()
        # Insert filtered entries
        try:
            for entry in all_entries:
                if not _entry_matches_filter(entry, name_tokens):
                    continue
                if not _entry_content_contains(entry, content_tokens):
                    continue
                audio_name, full_audio_path, size_str, modified_str, transcript, has_audio, txt_size_b, md_size_b = entry
                iid = tree.insert("", tk.END, values=(audio_name, size_str, modified_str, transcript, txt_size_b, md_size_b))
                if has_audio and full_audio_path:
                    path_to_item[full_audio_path] = iid
        except Exception:
            pass
        # Auto-fit for current view
        try:
            autofit_tree_columns(tree, cols, min_widths={"size": 80, "modified": 140}, padding=18)
        except Exception:
            pass

    # Debounce filter changes
    _filter_job = {"id": None}
    def _schedule_apply_filter(*_):
        try:
            if _filter_job["id"] is not None:
                try:
                    root.after_cancel(_filter_job["id"])
                except Exception:
                    pass
                _filter_job["id"] = None
            _filter_job["id"] = root.after(150, apply_filter)
        except Exception:
            apply_filter()

    # Bind changes in the filter entries
    try:
        current_filter_var.trace_add("write", lambda *_: _schedule_apply_filter())
        filter_entry.bind("<KeyRelease>", _schedule_apply_filter)
        content_filter_var.trace_add("write", lambda *_: _schedule_apply_filter())
        content_entry.bind("<KeyRelease>", _schedule_apply_filter)
    except Exception:
        pass

    # Lower: Notebook with Log, Preview, and Notes tabs
    nb = ttk.Notebook(paned)
    paned.add(nb, weight=1)

    # Configure minimal size for files pane to allow near-collapse
    try:
        paned.paneconfigure(files_frame, minsize=24)
    except Exception:
        pass

    # Files pane collapse/expand behavior
    files_collapsed = {"value": False}
    def _set_files_collapsed(collapsed: bool):
        files_collapsed["value"] = collapsed
        try:
            total_h = root.winfo_height()
            if total_h <= 1:
                total_h = 600
            if collapsed:
                # Move sash to top to minimize files pane
                paned.sashpos(0, 0)
                files_toggle_btn.configure(text="Files ▲")
            else:
                # Give about 22% to files, 78% to bottom
                paned.sashpos(0, int(total_h * 0.22))
                files_toggle_btn.configure(text="Files ▼")
        except Exception:
            pass

    def on_files_toggle():
        _set_files_collapsed(not files_collapsed["value"])

    try:
        files_toggle_btn.configure(command=on_files_toggle)
    except Exception:
        pass

    # Set initial sash position after layout to favor lower pane
    def _init_sash():
        _set_files_collapsed(False)
    root.after(120, _init_sash)

    # Log tab
    log_frame = tk.Frame(nb)
    log = tk.Text(log_frame, height=10, wrap="word")
    log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=log.yview)
    log.configure(state=tk.DISABLED, yscrollcommand=log_scroll.set)
    log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    nb.add(log_frame, text="Log")

    # Preview tab (zoomable)
    preview_frame = tk.Frame(nb)
    # Use a dedicated font so we can scale without affecting other widgets
    try:
        _base_preview_font = tkfont.nametofont("TkDefaultFont").copy()
    except Exception:
        _base_preview_font = tkfont.Font(family="Segoe UI", size=10)
    preview_font = tkfont.Font()
    try:
        preview_font.config(family=_base_preview_font.cget("family"), size=_base_preview_font.cget("size"))
    except Exception:
        preview_font.config(size=10)
    preview_zoom = {"size": preview_font.cget("size"), "min": 8, "max": 28, "base": preview_font.cget("size")}

    preview = tk.Text(preview_frame, height=10, wrap="word", font=preview_font)
    preview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    preview_scroll = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=preview.yview)
    preview.configure(state=tk.DISABLED, yscrollcommand=preview_scroll.set)
    preview_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _apply_preview_zoom(new_size: int):
        try:
            new_size = max(preview_zoom["min"], min(preview_zoom["max"], int(new_size)))
            preview_font.configure(size=new_size)
            preview_zoom["size"] = new_size
        except Exception:
            pass

    def _on_ctrl_mousewheel(event):
        # Windows: event.delta in multiples of 120; positive=up
        try:
            if (event.state & 0x4) == 0x4:  # Control pressed
                delta = event.delta if hasattr(event, "delta") else 0
                step = 1 if delta > 0 else -1
                _apply_preview_zoom(preview_zoom["size"] + step)
                return "break"
        except Exception:
            pass
        return None

    def _on_ctrl_plus(event):
        _apply_preview_zoom(preview_zoom["size"] + 1)
        return "break"

    def _on_ctrl_minus(event):
        _apply_preview_zoom(preview_zoom["size"] - 1)
        return "break"

    def _on_ctrl_zero(event):
        _apply_preview_zoom(preview_zoom["base"])
        return "break"

    # Bind zoom gestures
    try:
        preview.bind("<Control-MouseWheel>", _on_ctrl_mousewheel)      # Windows
        preview.bind("<Control-Button-4>", lambda e: (_apply_preview_zoom(preview_zoom["size"] + 1), "break"))  # Linux scroll up
        preview.bind("<Control-Button-5>", lambda e: (_apply_preview_zoom(preview_zoom["size"] - 1), "break"))  # Linux scroll down
        preview.bind("<Control-plus>", _on_ctrl_plus)
        preview.bind("<Control-KP_Add>", _on_ctrl_plus)
        preview.bind("<Control-minus>", _on_ctrl_minus)
        preview.bind("<Control-KP_Subtract>", _on_ctrl_minus)
        preview.bind("<Control-0>", _on_ctrl_zero)
        preview.bind("<Control-KP_0>", _on_ctrl_zero)
    except Exception:
        pass

    nb.add(preview_frame, text="Preview")

    # V2A controls are provided in the upper toolbar notebook; no V2A tab in lower notebook.

    # Hide original inline controls to avoid duplicates on the main toolbar row
    try:
        # Model controls
        model_label.pack_forget()
        model_combo.pack_forget()
        load_model_btn.pack_forget()
    except Exception:
        pass
    try:
        # Language and output controls
        language_label.pack_forget()
        indian_bias_chk.pack_forget()
        stability_chk.pack_forget()
        fast_decode_chk.pack_forget()
        language_combo.pack_forget()
        output_label.pack_forget()
        output_mode_combo.pack_forget()
    except Exception:
        pass
    try:
        # Recent controls and width buttons
        recent_label.pack_forget()
        recent_combo.pack_forget()
        dec_btn.pack_forget(); inc_btn.pack_forget(); recent_open_btn.pack_forget()
    except Exception:
        pass

    # Notes (Markdown) tab
    notes_frame = tk.Frame(nb)
    notes_toolbar = tk.Frame(notes_frame)
    notes_toolbar.pack(fill=tk.X, padx=6, pady=(6, 4))
    current_md_path_var = tk.StringVar(value="")
    # Helper to shorten long paths with middle ellipsis
    def _shorten_middle(text: str, max_len: int = 80) -> str:
        try:
            t = text or ""
            if len(t) <= max_len:
                return t
            keep = max_len - 3
            left = keep // 2
            right = keep - left
            return f"{t[:left]}...{t[-right:]}"
        except Exception:
            return text
    display_md_path_var = tk.StringVar(value="")
    def _refresh_md_path(*_):
        display_md_path_var.set(_shorten_middle(current_md_path_var.get(), 100))
    try:
        current_md_path_var.trace_add("write", _refresh_md_path)
    except Exception:
        pass
    tk.Label(notes_toolbar, text="Notes file:").pack(side=tk.LEFT)
    notes_path_label = tk.Label(notes_toolbar, textvariable=display_md_path_var, anchor="w")
    notes_path_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 6))
    autosave_enabled_var = tk.BooleanVar(value=True)
    autosave_delay_s_var = tk.DoubleVar(value=1.0)  # seconds
    tk.Label(notes_toolbar, text="Auto-save:").pack(side=tk.LEFT, padx=(6, 2))
    autosave_chk = tk.Checkbutton(notes_toolbar, text="Notes", variable=autosave_enabled_var)
    autosave_chk.pack(side=tk.LEFT)
    tk.Label(notes_toolbar, text="Delay:").pack(side=tk.LEFT, padx=(8, 2))
    autosave_delay_spin = tk.Spinbox(notes_toolbar, from_=0.2, to=10.0, increment=0.2, width=5, textvariable=autosave_delay_s_var)
    autosave_delay_spin.pack(side=tk.LEFT)
    tk.Label(notes_toolbar, text="s").pack(side=tk.LEFT, padx=(2, 6))
    # Autosave scheduling state holder used by _perform_autosave/_schedule_autosave
    # Use a mutable dict so inner functions can update without nonlocal
    _autosave_job = {"id": None}
    # Right-aligned sub-toolbar to keep everything on one row
    notes_toolbar_right = tk.Frame(notes_toolbar)
    notes_toolbar_right.pack(side=tk.RIGHT)
    saved_at_var = tk.StringVar(value="")
    saved_at_label = tk.Label(notes_toolbar_right, textvariable=saved_at_var, anchor="e", fg="#0a7")
    notes_reveal_btn = tk.Button(notes_toolbar_right, text="Reveal", width=10)
    notes_reveal_btn.pack(side=tk.RIGHT, padx=(6, 0))
    notes_save_btn = tk.Button(notes_toolbar_right, text="Save", width=10)
    notes_save_btn.pack(side=tk.RIGHT, padx=(6, 0))
    def _derive_md_path_for_autosave() -> str:
        """Compute a sensible .md target without prompting the user.
        Prefer existing current_md_path_var; else derive from selected row.
        Return empty string if no reasonable path can be determined.
        """
        try:
            md_path = (current_md_path_var.get() or "").strip()
            if md_path:
                return md_path
            # Fall back to current selection in the tree
            sel = tree.selection()
            iid = sel[0] if sel else ""
            if not iid:
                return ""
            vals = tree.item(iid, "values") or []
            if not vals:
                return ""
            # Derive audio-based candidate from display name and current folder
            audio_disp = str(vals[0]) if len(vals) > 0 else ""
            if audio_disp.startswith("🎥 "):
                audio_disp = audio_disp[2:].lstrip()
            base_name = audio_disp.replace(" (md only)", "").replace(" (no audio)", "").strip()
            # Strip any extension so autosave target is base.md, not base.mp3.md
            try:
                base_name = os.path.splitext(base_name)[0]
            except Exception:
                pass
            folder = (current_folder_var.get() or "").strip()
            if folder and base_name:
                return os.path.join(folder, base_name + ".md")
            # As a fallback, try transcript-based target if present
            txt_path = vals[3] if len(vals) >= 4 else ""
            if isinstance(txt_path, str) and txt_path:
                try:
                    folder2 = os.path.dirname(txt_path)
                    base2, _ = os.path.splitext(os.path.basename(txt_path))
                    if folder2 and base2:
                        return os.path.join(folder2, base2 + ".md")
                except Exception:
                    pass
        except Exception:
            pass
        return ""

    def _perform_autosave():
        # Clear scheduled job marker first
        _autosave_job["id"] = None
        try:
            if not autosave_enabled_var.get():
                return
        except Exception:
            return
        # Determine target path (create if needed, silently)
        md_path = _derive_md_path_for_autosave()
        if not md_path:
            return
        # Normalize md_path: collapse cases like name.mp3.md -> name.md
        try:
            base_fn = os.path.basename(md_path)
            root_no_md, ext_md = os.path.splitext(base_fn)
            if ext_md.lower() == ".md":
                # If root_no_md itself has a media/text extension, strip it
                media_exts = {".mp3", ".wav", ".m4a", ".flac", ".aac", ".wma", ".ogg", ".opus", ".mp4", ".mkv", ".mov", ".avi", ".wmv", ".webm", ".m4v", ".txt", ".md"}
                stem, ext2 = os.path.splitext(root_no_md)
                if ext2.lower() in media_exts and stem:
                    md_path = os.path.join(os.path.dirname(md_path), stem + ".md")
        except Exception:
            pass
        try:
            os.makedirs(os.path.dirname(md_path), exist_ok=True)
            content = notes_editor.get("1.0", tk.END)
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(content)
            try:
                current_md_path_var.set(md_path)
            except Exception:
                pass
            # Update saved-at label
            try:
                saved_at_var.set(f"Saved at {datetime.now().strftime('%H:%M:%S')}")
            except Exception:
                pass
            # Log autosave to the Log tab
            try:
                append_log(f"Autosaved notes → {md_path}")
            except Exception:
                pass
            # Refresh preview after save
            try:
                render_markdown_to_preview(content)
            except Exception:
                pass
        except Exception:
            # Best-effort; ignore autosave errors
            pass

    def _schedule_autosave(event=None):
        try:
            if not autosave_enabled_var.get():
                return
            # Cancel previous pending job
            if _autosave_job["id"] is not None:
                try:
                    root.after_cancel(_autosave_job["id"])
                except Exception:
                    pass
                _autosave_job["id"] = None
            delay_ms = int(max(200, float(autosave_delay_s_var.get()) * 1000))
            _autosave_job["id"] = root.after(delay_ms, _perform_autosave)
        except Exception:
            pass
    
    # Markdown formatting toolbar (above editor)
    md_format_toolbar = tk.Frame(notes_frame)
    md_format_toolbar.pack(fill=tk.X, padx=6, pady=(0, 4))
    # Left side: language dropdown for code blocks (remembers last used)
    md_lang_frame = tk.Frame(md_format_toolbar)
    md_lang_frame.pack(side=tk.LEFT)
    tk.Label(md_lang_frame, text="Lang:").pack(side=tk.LEFT, padx=(0, 4))
    common_langs = [
        "python", "bash", "sh", "powershell", "cmd", "bat",
        "json", "yaml", "markdown", "text",
        "javascript", "typescript", "html", "css",
        "c", "cpp", "java", "go", "rust", "sql",
        "matlab", "r"
    ]
    code_lang_var = tk.StringVar(value="python")
    code_lang_combo = ttk.Combobox(md_lang_frame, textvariable=code_lang_var, values=common_langs, width=12, state="normal")
    code_lang_combo.pack(side=tk.LEFT)
    # Right-aligned area for engine indicator
    md_toolbar_right = tk.Frame(md_format_toolbar)
    md_toolbar_right.pack(side=tk.RIGHT)
    preview_engine_var = tk.StringVar(value="")
    tk.Label(md_toolbar_right, textvariable=preview_engine_var, fg="#666").pack(side=tk.RIGHT, padx=(6, 0))

    def _get_selection_or_cursor():
        try:
            start = notes_editor.index("sel.first")
            end = notes_editor.index("sel.last")
            return start, end, True
        except Exception:
            # No selection; operate at cursor
            idx = notes_editor.index(tk.INSERT)
            return idx, idx, False

    def _refresh_after_edit():
        try:
            # Trigger existing preview/autosave debounce
            notes_editor.event_generate("<KeyRelease>")
        except Exception:
            try:
                content = notes_editor.get("1.0", tk.END)
                render_markdown_to_preview(content)
            except Exception:
                pass

    def _wrap_selection(prefix: str, suffix: str):
        s, e, has_sel = _get_selection_or_cursor()
        if has_sel:
            text = notes_editor.get(s, e)
            notes_editor.delete(s, e)
            notes_editor.insert(s, f"{prefix}{text}{suffix}")
        else:
            notes_editor.insert(s, f"{prefix}{suffix}")
            # Place cursor between
            try:
                notes_editor.mark_set(tk.INSERT, f"{s}+{len(prefix)}c")
            except Exception:
                pass
        _refresh_after_edit()

    def _linewise_prefix(prefix: str):
        # Apply prefix to each selected line, or current line
        s, e, has_sel = _get_selection_or_cursor()
        start_line = int(float(s.split(".")[0]))
        end_line = int(float(e.split(".")[0])) if has_sel else start_line
        for ln in range(start_line, end_line + 1):
            line_start = f"{ln}.0"
            notes_editor.insert(line_start, prefix)
        _refresh_after_edit()

    def _heading(level: int):
        s, _, _ = _get_selection_or_cursor()
        line = int(float(s.split(".")[0]))
        line_start = f"{line}.0"
        # Remove existing hashes on this line, then add desired level
        try:
            line_text = notes_editor.get(line_start, f"{line}.end")
        except Exception:
            line_text = ""
        stripped = line_text.lstrip('# ').rstrip('\n')
        notes_editor.delete(line_start, f"{line}.end")
        notes_editor.insert(line_start, f"{'#'*level} {stripped}\n")
        _refresh_after_edit()

    def _make_link():
        s, e, has_sel = _get_selection_or_cursor()
        if has_sel:
            text = notes_editor.get(s, e)
            notes_editor.delete(s, e)
            notes_editor.insert(s, f"[{text}]()")
            try:
                notes_editor.mark_set(tk.INSERT, f"{s}+{len(text)+3}c")
            except Exception:
                pass
        else:
            notes_editor.insert(s, "[link text]()")
            try:
                notes_editor.mark_set(tk.INSERT, f"{s}+1c")
            except Exception:
                pass
        _refresh_after_edit()

    def _inline_code():
        s, e, has_sel = _get_selection_or_cursor()
        if has_sel:
            text = notes_editor.get(s, e)
            if "\n" in text:
                # Multiline -> code block
                notes_editor.delete(s, e)
                notes_editor.insert(s, f"```\n{text}\n```\n")
            else:
                notes_editor.delete(s, e)
                notes_editor.insert(s, f"`{text}`")
        else:
            notes_editor.insert(s, "``")
            try:
                notes_editor.mark_set(tk.INSERT, f"{s}+1c")
            except Exception:
                pass
        _refresh_after_edit()

    def _code_block():
        # Prompt for language (optional)
        try:
            lang = simpledialog.askstring(
                "Code Block",
                "Language (e.g., python, bash) — optional:",
                initialvalue=(code_lang_var.get() or ""),
                parent=root,
            )
        except Exception:
            lang = None
        lang = (lang or "").strip()
        if lang:
            try:
                code_lang_var.set(lang)
            except Exception:
                pass
        s, e, has_sel = _get_selection_or_cursor()
        if has_sel:
            text = notes_editor.get(s, e)
            notes_editor.delete(s, e)
            notes_editor.insert(s, f"```{lang}\n{text}\n```\n")
            # Place cursor just after the closing fence
            try:
                notes_editor.mark_set(tk.INSERT, f"{s}+{len(lang)+4+len(text)+5}c")
            except Exception:
                pass
        else:
            # Insert empty fenced block and position cursor on the blank line inside
            block = f"```{lang if lang else (code_lang_var.get() or '')}\n\n```\n"
            notes_editor.insert(s, block)
            try:
                # Move cursor one line down after opening fence
                effective_lang = lang if lang else (code_lang_var.get() or '')
                notes_editor.mark_set(tk.INSERT, f"{s}+{len(effective_lang)+4}c")  # after first line break
                notes_editor.mark_set(tk.INSERT, f"{tk.INSERT}+1l")
            except Exception:
                pass
        _refresh_after_edit()

    def _image():
        s, _, _ = _get_selection_or_cursor()
        notes_editor.insert(s, "![alt text](images/placeholder.png)")
        _refresh_after_edit()

    def _insert_image_action():
        # Pick an image and either copy it into notes images/ or link it directly, then insert markdown
        try:
            img_path = filedialog.askopenfilename(
                title="Insert image",
                filetypes=[
                    ("Images", "*.png *.jpg *.jpeg *.gif *.bmp *.webp *.svg"),
                    ("All files", "*.*"),
                ],
            )
            if not img_path:
                return
            img_path = os.path.abspath(img_path)
            # Determine target folder (images under current md, else under current folder)
            try:
                base_dir = os.path.dirname(current_md_path_var.get()) if current_md_path_var.get() else (current_folder_var.get() or os.getcwd())
            except Exception:
                base_dir = os.getcwd()
            images_dir = os.path.join(base_dir, "images")
            os.makedirs(images_dir, exist_ok=True)

            # Ask whether to copy into images folder (recommended for portability)
            do_copy = messagebox.askyesno(
                "Insert Image",
                "Copy image into the notes 'images' folder?\n\nYes: copy into images/ and use a relative path.\nNo: link to the original absolute path.",
                parent=root,
            )

            if do_copy:
                target_name = os.path.basename(img_path)
                dest_path = os.path.join(images_dir, target_name)
                # Avoid overwriting: if exists, add numeric suffix
                if os.path.abspath(dest_path) != os.path.abspath(img_path) and os.path.exists(dest_path):
                    name, ext = os.path.splitext(target_name)
                    k = 2
                    while os.path.exists(os.path.join(images_dir, f"{name}-{k}{ext}")):
                        k += 1
                    dest_path = os.path.join(images_dir, f"{name}-{k}{ext}")
                try:
                    if os.path.abspath(dest_path) != os.path.abspath(img_path):
                        shutil.copy2(img_path, dest_path)
                    # Insert relative markdown path
                    rel = os.path.relpath(dest_path, start=base_dir).replace("\\", "/")
                    _wrap_selection(f"![alt text](", f"{rel})")
                except Exception as e:
                    messagebox.showerror("Insert Image", f"Failed to copy image. Linking instead.\n\n{e}")
                    _wrap_selection(f"![alt text](", f"{img_path})")
            else:
                # Link to original absolute path; preprocessing will turn into file:///
                _wrap_selection(f"![alt text](", f"{img_path})")
        except Exception as e:
            messagebox.showerror("Insert Image", f"Unexpected error: {e}")

    def _numbered():
        s, e, has_sel = _get_selection_or_cursor()
        start_line = int(float(s.split(".")[0]))
        end_line = int(float(e.split(".")[0])) if has_sel else start_line
        num = 1
        for ln in range(start_line, end_line + 1):
            notes_editor.insert(f"{ln}.0", f"{num}. ")
            num += 1
        _refresh_after_edit()

    # Buttons
    btn_specs = [
        ("B", lambda: _wrap_selection("**", "**")),
        ("I", lambda: _wrap_selection("*", "*")),
        ("H1", lambda: _heading(1)),
        ("H2", lambda: _heading(2)),
        ("•", lambda: _linewise_prefix("- ")),
        ("1.", _numbered),
        ("Link", _make_link),
        ("Code", _inline_code),
        ("Code Block", _code_block),
        (">", lambda: _linewise_prefix("> ")),
        ("Img", _image),
        ("Insert Image…", _insert_image_action),
        ("[ ]", lambda: _linewise_prefix("- [ ] ")),
    ]

    for text, cmd in btn_specs:
        tk.Button(md_format_toolbar, text=text, width=3, command=cmd).pack(side=tk.LEFT, padx=2)

    # Split view: editor | preview
    notes_split = ttk.Panedwindow(notes_frame, orient=tk.HORIZONTAL)
    notes_split.pack(fill=tk.BOTH, expand=True)
    # Left: editor with its own scroll
    editor_container = tk.Frame(notes_split)
    notes_editor = tk.Text(editor_container, height=10, wrap="word")
    notes_editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    notes_scroll = ttk.Scrollbar(editor_container, orient=tk.VERTICAL, command=notes_editor.yview)
    notes_editor.configure(yscrollcommand=notes_scroll.set)
    notes_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    try:
        # Debounced autosave on typing
        notes_editor.bind("<KeyRelease>", _schedule_autosave)
        # Also autosave when the editor loses focus
        notes_editor.bind("<FocusOut>", lambda e: (_schedule_autosave(), None))
    except Exception:
        pass
    # Right: rendered preview
    preview_container = tk.Frame(notes_split)
    if HtmlFrame is not None:
        md_preview = HtmlFrame(preview_container, horizontal_scrollbar="auto")
        md_preview.pack(fill=tk.BOTH, expand=True)
        preview_engine_var.set("Preview: tkinterweb")
    elif HTMLLabel is not None:
        md_preview = HTMLLabel(preview_container, html="", background="white")
        md_preview.pack(fill=tk.BOTH, expand=True)
        preview_engine_var.set("Preview: tkhtmlview")
    else:
        # Fallback to read-only text if HTML renderer unavailable
        md_preview = tk.Text(preview_container, height=10, wrap="word", state=tk.DISABLED)
        md_preview.pack(fill=tk.BOTH, expand=True)
        preview_engine_var.set("Preview: text (fallback)")
    notes_split.add(editor_container, weight=1)
    notes_split.add(preview_container, weight=1)
    nb.add(notes_frame, text="Notes (Markdown)")

    # When switching to Notes tab, ensure focus and autosave target, then schedule autosave soon
    def _on_notes_tab_selected():
        try:
            # If no md path yet, derive one so autosave has a destination
            if not (current_md_path_var.get() or "").strip():
                md_guess = _derive_md_path_for_autosave()
                if md_guess:
                    current_md_path_var.set(md_guess)
        except Exception:
            pass
        try:
            notes_editor.focus_set()
        except Exception:
            pass
        # Schedule a near-immediate autosave to establish the file
        try:
            # small delay to allow focus/layout to settle
            root.after(150, _perform_autosave)
        except Exception:
            pass

    def _on_preview_tab_selected():
        try:
            sel = tree.selection()
            iid = sel[0] if sel else ""
            if iid:
                load_preview_for_item(iid)
            else:
                set_preview_text("")
        except Exception:
            # Non-fatal: leave preview as-is
            pass

    def _on_nb_tab_changed(event):
        try:
            w = event.widget
            # Only handle our bottom notebook
            if w is nb:
                cur = nb.select()
                if cur:
                    tab = nb.nametowidget(cur)
                    if tab is notes_frame:
                        _on_notes_tab_selected()
                    elif tab is preview_frame:
                        _on_preview_tab_selected()
        except Exception:
            pass
    try:
        nb.bind("<<NotebookTabChanged>>", _on_nb_tab_changed)
    except Exception:
        pass

    # --- Menubar with Tools -> Clear Cache & Reset Whisper Cache ---
    try:
        menubar = tk.Menu(root)
        root.config(menu=menubar)
        tools_menu = tk.Menu(menubar, tearoff=0)
        # menubar.add_cascade(label="Tools", menu=tools_menu)

        def clear_cached_wavs():
            cache_dir = os.path.join(os.path.expanduser("~"), ".audio2text_cache")
            if not os.path.isdir(cache_dir):
                messagebox.showinfo("Clear Cache", "No cache directory found.")
            removed = 0
            errors = []
            try:
                for name in os.listdir(cache_dir):
                    if not name.lower().endswith(".wav"):
                        continue
                    p = os.path.join(cache_dir, name)
                    try:
                        os.remove(p)
                        removed += 1
                    except Exception as e:
                        errors.append(f"{name}: {e}")
                # Try to remove cache dir if empty (ignore errors)
                try:
                    if not os.listdir(cache_dir):
                        os.rmdir(cache_dir)
                except Exception:
                    pass
            except Exception as e:
                messagebox.showerror("Clear Cache", f"Failed to enumerate cache directory:\n{e}")
                return
            if errors:
                messagebox.showerror("Clear Cache", f"Removed {removed} file(s), but some failed:\n" + "\n".join(errors))
            else:
                messagebox.showinfo("Clear Cache", f"Removed {removed} cached WAV file(s).")

        tools_menu.add_command(label="Clear Cached WAVs", command=clear_cached_wavs)

        def reset_whisper_cache():
            primary_cache = os.path.join(os.path.expanduser("~"), ".cache", "whisper")
            alt_cache = os.path.join(os.getcwd(), "whisper_models_cache")
            removed = []
            errors = []
            for base in [primary_cache, alt_cache]:
                try:
                    if not os.path.isdir(base):
                        continue
                    for name in os.listdir(base):
                        p = os.path.join(base, name)
                        if os.path.isfile(p) and name.lower().endswith(".pt"):
                            try:
                                os.remove(p)
                                removed.append(p)
                            except Exception as e:
                                errors.append(f"{p}: {e}")
                except Exception as e:
                    errors.append(f"{base}: {e}")
            if errors:
                messagebox.showerror("Reset Whisper Cache", "Some files could not be removed:\n" + "\n".join(errors))
            else:
                messagebox.showinfo("Reset Whisper Cache", f"Removed {len(removed)} cached model file(s).")

        tools_menu.add_command(label="Reset Whisper Cache", command=reset_whisper_cache)
    except Exception:
        pass

    # Saved transcript entry row
    out_frame = tk.Frame(root)
    out_frame.pack(fill=tk.X, padx=12, pady=(0, 8))
    tk.Label(out_frame, text="Saved transcript:").pack(side=tk.LEFT)
    out_entry = tk.Entry(out_frame, textvariable=output_path_var)
    out_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 6))

    # Context menu helpers
    def _normpath(p: str) -> str:
        try:
            return os.path.normpath(p) if p else p
        except Exception:
            return p

    def _win_long_path(p: str) -> str:
        """On Windows, convert to extended-length path when needed.
        Keeps normal paths otherwise. Accepts any input and returns a usable path string.
        """
        try:
            if not p:
                return p
            ap = os.path.abspath(p)
            # Only apply on Windows and for local paths (not already extended or UNC)
            if os.name == 'nt':
                # If already extended-length or UNC with \\?\ prefix, keep as-is
                if ap.startswith('\\\\?\\'):
                    return ap
                # For very long paths, prefix with \\?\
                if len(ap) >= 240:
                    # Ensure backslashes for Windows extended paths
                    ap = ap.replace('/', '\\')
                    return '\\\\?\\' + ap
            return ap
        except Exception:
            return p

    def copy_to_clipboard(text: str):
        try:
            root.clipboard_clear()
            root.clipboard_append(text)
            root.update()
        except Exception:
            pass

    def reveal_in_explorer(path: str):
        if not path:
            return
        # Normalize to absolute for Explorer
        abs_path = os.path.abspath(path)
        try:
            if os.path.isfile(abs_path):
                # Use separate args to avoid quoting issues with spaces
                subprocess.run(["explorer", "/select,", abs_path], check=False)
                return
            # If it's a directory, open it directly
            if os.path.isdir(abs_path):
                subprocess.run(["explorer", abs_path], check=False)
                return
            # If it doesn't exist, try opening its parent folder
            parent = os.path.dirname(abs_path)
            if parent and os.path.isdir(parent):
                subprocess.run(["explorer", parent], check=False)
        except Exception:
            pass

    def open_with_default_app(path: str):
        try:
            if path and os.path.isfile(path):
                os.startfile(path)  # Windows: open with default application
        except Exception:
            messagebox.showerror("Open Failed", f"Could not open file:\n{path}")

    # --- URL transcription helpers ---
    def _download_media_to_temp(url: str) -> tuple[str | None, str | None]:
        """Download media from URL into a unique temp directory using yt-dlp.
        Returns (media_path, temp_dir). Caller is responsible for cleaning temp_dir if desired.
        """
        tmpdir = tempfile.mkdtemp(prefix="a2t_url_")

        # 1) If the URL looks like a direct media file (e.g., googlevideo.com or ends with media extension),
        # try a simple HTTP download first without yt-dlp.
        def _looks_like_direct_media(u: str) -> bool:
            try:
                low = (u or "").lower()
                media_exts = (".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg", ".wma", ".mp4", ".webm", ".mkv", ".mov", ".avi")
                return low.endswith(media_exts) or ("googlevideo.com" in low)
            except Exception:
                return False

        if _looks_like_direct_media(url):
            try:
                import urllib.request
                # Guess a filename
                filename = "downloaded_media"
                # Try to infer extension from URL query if present
                if ".mp4" in url.lower():
                    filename += ".mp4"
                elif ".webm" in url.lower():
                    filename += ".webm"
                elif ".m4a" in url.lower():
                    filename += ".m4a"
                elif ".mp3" in url.lower():
                    filename += ".mp3"
                else:
                    # default to mp4 for video URLs like googlevideo
                    filename += ".mp4"
                dest = os.path.join(tmpdir, filename)
                set_status("Downloading media (direct)...")
                # Some hosts require a User-Agent
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req) as r, open(dest, "wb") as f:
                    shutil.copyfileobj(r, f)
                if os.path.isfile(dest) and os.path.getsize(dest) > 0:
                    return dest, tmpdir
            except Exception as e:
                append_log(f"Direct download attempt failed, falling back to yt-dlp: {e}")

        # 2) Fallback to yt-dlp for complex URLs (watch pages, playlists, etc.)
        ok = ensure_yt_dlp_installed()
        if not ok:
            return None, tmpdir
        # Use yt-dlp via module invocation for compatibility
        out_tmpl = os.path.join(tmpdir, "%(title)s.%(ext)s")
        cmd = [sys.executable, "-m", "yt_dlp", "-f", "bestaudio/best", "-o", out_tmpl, url]
        try:
            set_status("Downloading media...")
            completed = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if completed.returncode != 0:
                append_log("yt-dlp download failed. stderr:\n" + (completed.stderr or ""))
                return None, tmpdir
        except Exception as e:
            append_log(f"yt-dlp download failed: {e}")
            return None, tmpdir
        # Find the largest/newest file in tmpdir
        try:
            files = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if os.path.isfile(os.path.join(tmpdir, f))]
            if not files:
                return None, tmpdir
            files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
            return files[0], tmpdir
        except Exception:
            return None, tmpdir

    # --- Media helpers ---
    def is_video_file(path: str) -> bool:
        try:
            _, ext = os.path.splitext(path or "")
            return (ext or "").lower() in {
                ".mp4", ".mov", ".mkv", ".avi", ".wmv", ".m4v", ".webm", ".mts", ".m2ts", ".ts",
                ".3gp", ".flv", ".mpeg",
            }
        except Exception:
            return False

    def display_to_real_filename(name: str) -> str:
        # Strip our optional leading video emoji tag and optional trailing indicator
        try:
            if name.startswith("🎥 "):
                name = name[2:].lstrip()
            if name.endswith(" [video]"):
                name = name[:-8]
            return name
        except Exception:
            return name

    def _file_size_bytes(path: str) -> int:
        try:
            return os.path.getsize(path)
        except Exception:
            return 0

    def _cache_wav_path_for(src_path: str) -> str:
        import hashlib
        home = os.path.expanduser("~")
        cache_dir = os.path.join(home, ".audio2text_cache")
        try:
            os.makedirs(cache_dir, exist_ok=True)
        except Exception:
            pass
        try:
            stat = os.stat(src_path)
            key = f"{os.path.abspath(src_path)}|{stat.st_mtime_ns}|{stat.st_size}".encode("utf-8", errors="ignore")
        except Exception:
            key = os.path.abspath(src_path).encode("utf-8", errors="ignore")
        digest = hashlib.sha1(key).hexdigest()  # short enough for Windows paths
        return os.path.join(cache_dir, f"{digest}.wav")

    def get_or_make_cached_wav_for_large_video(input_path: str, threshold_mb: int = 200) -> str | None:
        """If input is a video and larger than threshold, extract audio to a cached WAV and return its path.
        Return None to use the original input file.
        """
        try:
            if not is_video_file(input_path):
                return None
            size_mb = _file_size_bytes(input_path) / (1024 * 1024.0)
            if size_mb < float(threshold_mb):
                return None
            out_wav = _cache_wav_path_for(input_path)
            if os.path.isfile(out_wav):
                return out_wav
            # Extract mono 16 kHz WAV using ffmpeg
            cmd = [
                "ffmpeg", "-y", "-i", input_path,
                "-vn", "-ac", "1", "-ar", "16000", "-f", "wav", out_wav,
            ]
            try:
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                if os.path.isfile(out_wav):
                    return out_wav
            except Exception as e:
                append_log(f"FFmpeg extraction failed: {e}")
            return None
        except Exception:
            return None

    def human_readable_size(num_bytes: int) -> str:
        """Return human-readable file size (e.g., 1.23 MB)."""
        try:
            size = float(num_bytes)
        except Exception:
            return "-"
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0 or unit == "TB":
                return f"{size:.2f} {unit}"
            size /= 1024.0

    def human_readable_mtime(ts: float) -> str:
        """Return human-readable modified time (local)."""
        try:
            return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
        except Exception:
            return "-"

    def autofit_tree_columns(tree_widget: ttk.Treeview, columns: tuple[str, ...], min_widths=None, max_widths=None, padding: int = 18):
        """Auto-fit column widths to content and headers.
        - min_widths/max_widths are optional dicts mapping column id to pixel width constraints.
        - padding adds some extra space so text isn't cramped.
        """
        try:
            # Use the Treeview's current font (falls back to default if not found)
            tv_font = tkfont.nametofont(str(tree_widget.cget("font"))) if tree_widget.cget("font") else tkfont.nametofont("TkDefaultFont")
        except Exception:
            tv_font = tkfont.nametofont("TkDefaultFont")

        min_widths = min_widths or {}
        max_widths = max_widths or {}

        # Measure each column
        for col in columns:
            # Start with header label text
            header_text = tree_widget.heading(col).get("text", col)
            max_px = tv_font.measure(header_text)

            # Include all row values in that column
            for iid in tree_widget.get_children(""):
                vals = tree_widget.item(iid, "values")
                if not vals:
                    continue
                # Map column to index
                try:
                    idx = columns.index(col)
                except ValueError:
                    idx = 0
                cell = vals[idx] if idx < len(vals) else ""
                # Avoid very long paths in transcript from blowing up width; clip for measurement but keep full text shown with horizontal scroll if any
                display_sample = str(cell)
                px = tv_font.measure(display_sample)
                if px > max_px:
                    max_px = px

            # Apply padding and constraints
            max_px += padding
            if col in min_widths:
                max_px = max(max_px, int(min_widths[col]))
            if col in max_widths:
                max_px = min(max_px, int(max_widths[col]))

            # Set width
            try:
                tree_widget.column(col, width=max_px)
            except Exception:
                pass

    # State for file browser
    current_folder_var = tk.StringVar(value="")
    path_to_item = {}

    # Recent folders state and helpers
    RECENT_FILE = os.path.join(os.path.expanduser("~"), ".audio2text_recent_folders.json")
    STATE_FILE = os.path.join(os.path.expanduser("~"), ".audio2text_state.json")
    MAX_RECENT = 10

    def load_recent_folders():
        try:
            if os.path.isfile(RECENT_FILE):
                with open(RECENT_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    # Keep only existing directories
                    vals = [p for p in data if isinstance(p, str) and os.path.isdir(p)]
                    # Update both recent widgets if available
                    try:
                        recent_combo["values"] = vals
                    except Exception:
                        pass
                    try:
                        recent_combo_tab["values"] = vals
                    except Exception:
                        pass
                    # Auto-fit to loaded values
                    try:
                        update_recent_combo_width(vals)
                    except Exception:
                        pass
                    return vals
        except Exception:
            pass
        try:
            recent_combo["values"] = []
        except Exception:
            pass
        try:
            recent_combo_tab["values"] = []
        except Exception:
            pass
        return []

    def save_recent_folders(values: list[str]):
        try:
            with open(RECENT_FILE, "w", encoding="utf-8") as f:
                json.dump(values[:MAX_RECENT], f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # --- Persist last-opened folder ---
    def load_last_folder() -> str:
        try:
            if os.path.isfile(STATE_FILE):
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    p = data.get("last_folder", "")
                    if isinstance(p, str) and os.path.isdir(p):
                        return p
        except Exception:
            pass
        return ""

    def save_last_folder(path: str):
        try:
            data = {}
            if os.path.isfile(STATE_FILE):
                try:
                    with open(STATE_FILE, "r", encoding="utf-8") as f:
                        existing = json.load(f)
                    if isinstance(existing, dict):
                        data.update(existing)
                except Exception:
                    pass
            data["last_folder"] = os.path.abspath(path)
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def set_recent_values(values: list[str]):
        vals = values[:MAX_RECENT]
        # Update both widgets' values
        try:
            recent_combo["values"] = vals
        except Exception:
            pass
        try:
            recent_combo_tab["values"] = vals
        except Exception:
            pass
        # If current value not in list, clear selection
        if recent_var.get() not in vals:
            recent_var.set("")
        # Auto-fit to provided values
        try:
            update_recent_combo_width(vals)
        except Exception:
            pass

    def add_recent_folder(path: str):
        if not path or not os.path.isdir(path):
            return
        path = os.path.abspath(path)
        # Merge current values from both widgets
        try:
            vals_a = list(recent_combo["values"]) if recent_combo["values"] else []
        except Exception:
            vals_a = []
        try:
            vals_b = list(recent_combo_tab["values"]) if recent_combo_tab["values"] else []
        except Exception:
            vals_b = []
        current_vals = []
        seen = set()
        for v in vals_a + vals_b:
            av = os.path.abspath(v)
            if av not in seen:
                seen.add(av)
                current_vals.append(v)
        # Move to front, remove duplicates
        new_vals = [path] + [p for p in current_vals if os.path.abspath(p) != path]
        new_vals = new_vals[:MAX_RECENT]
        set_recent_values(new_vals)
        save_recent_folders(new_vals)
        try:
            update_recent_combo_width(new_vals)
        except Exception:
            pass

    def open_recent_selected():
        path = recent_var.get().strip()
        if not path:
            return
        if not os.path.isdir(path):
            messagebox.showerror("Folder Missing", f"The folder no longer exists:\n{path}")
            # Remove from recent
            vals = [p for p in (recent_combo["values"] or []) if p != path]
            set_recent_values(vals)
            save_recent_folders(vals)
            return
        current_folder_var.set(path)
        append_log(f"Folder selected: {path}")
        populate_tree(path)
        # Persist last-opened folder
        try:
            save_last_folder(path)
        except Exception:
            pass

    def append_log(text: str):
        log.configure(state=tk.NORMAL)
        log.insert(tk.END, text + "\n")
        log.see(tk.END)
        log.configure(state=tk.DISABLED)

    def set_preview_text(text: str):
        # Sanitize citation markers for display in the preview tab only
        t = sanitize_notes_markdown(text if isinstance(text, str) else "")

        # --- Pre-process image links in Markdown to valid file:/// URLs (Windows safe) ---
        def _to_file_url(path: str, base_dir: str | None) -> str:
            try:
                p = path.strip().strip('"\'')
                # Ignore web URLs and data URIs
                lower = p.lower()
                if lower.startswith("http://") or lower.startswith("https://") or lower.startswith("data:"):
                    return p
                # Resolve relative paths against base_dir
                if base_dir and not os.path.isabs(p):
                    p_abs = os.path.abspath(os.path.join(base_dir, p))
                else:
                    p_abs = os.path.abspath(p)
                # Normalize to forward slashes and add file:/// scheme
                p_abs = p_abs.replace('\\', '/')
                # URL-encode path segments but keep slashes and colon
                quoted = urllib.parse.quote(p_abs, safe=':/')
                if not quoted.lower().startswith('file:///'):
                    quoted = 'file:///' + quoted
                return quoted
            except Exception:
                return path

        def _preprocess_markdown_images(md_text: str) -> str:
            try:
                import re
                base_dir = ''
                try:
                    # Prefer folder of current markdown file; else current folder
                    base_dir = os.path.dirname(current_md_path_var.get()) if current_md_path_var.get() else (current_folder_var.get() or '')
                except Exception:
                    base_dir = ''

                def repl(m):
                    alt = m.group(1)
                    url = m.group(2)
                    fixed = _to_file_url(url, base_dir)
                    return f"![{alt}]({fixed})"

                # Match standard markdown image: ![alt](url)
                return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", repl, md_text)
            except Exception:
                return md_text

        # Track missing local images to display a small warning in preview
        missing_list = []
        try:
            import re
            # Determine base_dir for resolving relative paths
            try:
                base_dir_detect = os.path.dirname(current_md_path_var.get()) if current_md_path_var.get() else (current_folder_var.get() or '')
            except Exception:
                base_dir_detect = ''

            def _resolve_to_fs(path_str: str) -> str:
                p = path_str.strip().strip('"\'')
                low = p.lower()
                if low.startswith("http://") or low.startswith("https://") or low.startswith("data:"):
                    return ""  # not a local file
                if base_dir_detect and not os.path.isabs(p):
                    p = os.path.abspath(os.path.join(base_dir_detect, p))
                return p

            for m in re.finditer(r"!\[[^\]]*\]\(([^)]+)\)", sanitized_input):
                candidate = _resolve_to_fs(m.group(1))
                if candidate and not os.path.isfile(candidate):
                    missing_list.append(candidate)
        except Exception:
            missing_list = []

        sanitized_input = _preprocess_markdown_images(sanitized_input)
        # Determine whether to show placeholder for empty input:
        # Only show placeholder if a real .md file exists for the current path.
        file_exists_for_notes = False
        try:
            p = current_md_path_var.get().strip()
            file_exists_for_notes = bool(p and os.path.isfile(p))
        except Exception:
            file_exists_for_notes = False

        if 'HtmlFrame' in locals() and HtmlFrame is not None:
            try:
                # Show placeholder only when an existing md is open; else keep empty
                has_text = bool(sanitized_input.strip())
                display_text = sanitized_input if has_text else ("# Notes\n\nWrite your notes here. Click 'Save Notes' to create the file." if file_exists_for_notes else "")
                exts = [
                    "extra", "toc", "sane_lists", "smarty", "nl2br", "fenced_code", "tables", "codehilite",
                ]
                ext_configs = {
                    'codehilite': {'noclasses': False, 'linenums': False, 'guess_lang': False}
                }
                if has_pymdown:
                    exts.extend([
                        "pymdownx.superfences", "pymdownx.highlight", "pymdownx.tasklist", "pymdownx.tilde", "pymdownx.caret", "pymdownx.emoji",
                    ])
                html = display_text
                if md_render is not None:
                    try:
                        html = md_render(display_text, extensions=exts, extension_configs=ext_configs)
                    except Exception:
                        try:
                            # Second pass minimal fallback
                            html = md_render(display_text, extensions=["fenced_code", "tables"]) 
                        except Exception:
                            html = display_text
                # Ensure code/pre have visible formatting even without Pygments
                if "<pre" in html:
                    html = html.replace("<pre>", '<pre style="background:#f6f8fa;padding:10px;border-radius:6px;overflow-x:auto;white-space:pre;">')
                    html = html.replace("<pre ", '<pre style="background:#f6f8fa;padding:10px;border-radius:6px;overflow-x:auto;white-space:pre;" ')
                if "<code" in html:
                    html = html.replace("<code>", '<code style="font-family:Consolas, \"Courier New\", monospace;">')
                    html = html.replace("<code ", '<code style="font-family:Consolas, \"Courier New\", monospace;" ')

                # Do not force a full-document <pre> fallback for HtmlFrame; let Markdown output stand

                # Use full HTML with a style block (HtmlFrame supports it)
                css = ""
                try:
                    from pygments.formatters import HtmlFormatter as _HtmlFormatter2
                    css = _HtmlFormatter2().get_style_defs('.codehilite')
                except Exception:
                    css = ""
                warn_html = ""
                if missing_list:
                    items = ''.join(f"<li>{os.path.basename(p)}</li>" for p in missing_list[:8])
                    more = "" if len(missing_list) <= 8 else f"<li>… and {len(missing_list)-8} more</li>"
                    warn_html = f"<div style='background:#fff3cd;border:1px solid #ffeeba;padding:6px 8px;border-radius:6px;margin-bottom:8px;color:#8a6d3b;'>Missing image file(s):<ul style='margin:4px 0 0 18px'>{items}{more}</ul></div>"
                # If there is truly no text and no warning, push a minimal blank page to clear old content
                if not display_text.strip() and not warn_html:
                    try:
                        md_preview.load_html("<html><head><meta charset='utf-8'></head><body></body></html>")
                    except Exception:
                        try:
                            md_preview.set_html("<div></div>")
                        except Exception:
                            pass
                    return
                full = f"""
                <html><head><meta charset='utf-8'>
                <style>
                body, div, p, li {{ font-family: Segoe UI, Arial, sans-serif; color: #222; }}
                table {{ border-collapse: collapse; }}
                table, th, td {{ border: 1px solid #999; }}
                th, td {{ padding: 6px 8px; }}
                pre {{ background: #f6f8fa; padding: 10px; border-radius: 6px; overflow-x: auto; }}
                code {{ background: #f6f8fa; padding: 2px 4px; border-radius: 4px; }}
                {css}
                </style></head><body>
                {warn_html}{html}
                </body></html>
                """
                try:
                    md_preview.load_html(full)
                except Exception:
                    # Some versions use set_html
                    md_preview.set_html(full)
            except Exception:
                try:
                    md_preview.load_html("<pre>Failed to render markdown.</pre>")
                except Exception:
                    pass
        elif 'HTMLLabel' in locals() and HTMLLabel is not None:
            try:
                # Show placeholder only when an existing md is open; else keep empty
                has_text = bool(sanitized_input.strip())
                display_text = sanitized_input if has_text else ("# Notes\n\nWrite your notes here. Click 'Save Notes' to create the file." if file_exists_for_notes else "")
                html = display_text
                if md_render is not None:
                    # Build extension set for richer formatting, with inline styles for codehilite
                    exts = [
                        "extra",
                        "toc",
                        "sane_lists",
                        "smarty",
                        "nl2br",
                        "fenced_code",
                        "tables",
                        "codehilite",
                    ]
                    ext_configs = {
                        'codehilite': {
                            'noclasses': True,   # use inline styles so we don't need a <style> block
                            'linenums': False,
                            'guess_lang': False,
                        }
                    }
                    if has_pymdown:
                        exts.extend([
                            "pymdownx.superfences",
                            "pymdownx.highlight",
                            "pymdownx.tasklist",
                            "pymdownx.tilde",
                            "pymdownx.caret",
                            "pymdownx.emoji",
                        ])
                        # prefer inline styles for pymdown highlight as well
                        ext_configs['pymdownx.highlight'] = {
                            'use_pygments': True,
                            'noclasses': True,
                        }
                    try:
                        html = md_render(display_text, extensions=exts, extension_configs=ext_configs)
                    except Exception:
                        # Fallback to basic
                        try:
                            html = md_render(display_text, extensions=["fenced_code", "tables"]) 
                        except Exception:
                            html = display_text

                # Post-process to force table borders via attributes/styles for tkhtmlview
                try:
                    if "<table" in html:
                        # Simplify sections that tkhtmlview may ignore
                        html = html.replace("<thead>", "").replace("</thead>", "")
                        html = html.replace("<tbody>", "").replace("</tbody>", "")
                        # Convert headers to regular cells (boldness is less important than borders showing)
                        html = html.replace("<th ", "<td ").replace("</th>", "</td>")
                        html = html.replace("<th>", "<td>")
                        html = html.replace(
                            "<table>",
                            '<table border="1" rules="all" frame="box" cellspacing="0" cellpadding="6" style="border-collapse:collapse;border:1px solid #999;">'
                        )
                        html = html.replace(
                            "<table ",
                            '<table border="1" rules="all" frame="box" cellspacing="0" cellpadding="6" style="border-collapse:collapse;border:1px solid #999;" '
                        )
                        html = html.replace(
                            "<td>",
                            '<td border="1" style="border:1px solid #999; padding:6px 8px;">'
                        )
                        # Also handle tags with attributes
                        html = html.replace(
                            "<td ",
                            '<td border="1" style="border:1px solid #999; padding:6px 8px;" '
                        )
                        # Add borders to table rows as well
                        html = html.replace(
                            "<tr>",
                            '<tr style="border:1px solid #999;">'
                        )
                        html = html.replace(
                            "<tr ",
                            '<tr style="border:1px solid #999;" '
                        )
                except Exception:
                    pass

                # Ensure code/pre have visible formatting with inline styles
                if "<pre" in html:
                    html = html.replace("<pre>", '<pre style="background:#f6f8fa;padding:10px;border-radius:6px;overflow-x:auto;white-space:pre;">')
                    html = html.replace("<pre ", '<pre style="background:#f6f8fa;padding:10px;border-radius:6px;overflow-x:auto;white-space:pre;" ')
                if "<code" in html:
                    html = html.replace("<code>", '<code style="font-family:Consolas, \"Courier New\", monospace;">')
                    html = html.replace("<code ", '<code style="font-family:Consolas, \"Courier New\", monospace;" ')

                # Fallback: if fenced markers present but no <pre>, convert only fenced blocks via regex
                if "<pre" not in html and ("```" in display_text or "~~~" in display_text):
                    import re, html as _py_html
                    def _fence_to_pre(m):
                        code = m.group(2) if m.group(2) is not None else m.group(1)
                        return f'<pre style="background:#f6f8fa;padding:10px;border-radius:6px;overflow-x:auto;white-space:pre;">{_py_html.escape(code)}</pre>'
                    # ```lang\ncode\n``` or ```\ncode\n```
                    html = re.sub(r"```[a-zA-Z0-9_-]*\n([\s\S]*?)\n```", lambda m: _fence_to_pre(m), display_text)
                    # ~~~ variant
                    html = re.sub(r"~~~[a-zA-Z0-9_-]*\n([\s\S]*?)\n~~~", lambda m: _fence_to_pre(m), html)

                # Wrap with minimal inline styling accepted by tkhtmlview (no <style> tag)
                container_style = (
                    "font-family: Segoe UI, Arial, sans-serif; color: #222;"
                )
                # Inline pre/code/table styling by wrapping in a div
                warn_html = ""
                if missing_list:
                    items = ''.join(f"<li>{os.path.basename(p)}</li>" for p in missing_list[:8])
                    more = "" if len(missing_list) <= 8 else f"<li>… and {len(missing_list)-8} more</li>"
                    warn_html = f"<div style='background:#fff3cd;border:1px solid #ffeeba;padding:6px 8px;border-radius:6px;margin-bottom:8px;color:#8a6d3b;'>Missing image file(s):<ul style='margin:4px 0 0 18px'>{items}{more}</ul></div>"
                # If there is no text and no warning, push a minimal blank container to clear old content
                if not has_text and not warn_html:
                    try:
                        md_preview.set_html("<div></div>")
                    except Exception:
                        pass
                else:
                    styled = f"<div style=\"{container_style}\">{warn_html}{html}</div>"
                    md_preview.set_html(styled)
            except Exception:
                try:
                    md_preview.set_html("<pre>Failed to render markdown.</pre>")
                except Exception:
                    pass
        else:
            try:
                md_preview.configure(state=tk.NORMAL)
                md_preview.delete("1.0", tk.END)
                md_preview.insert(tk.END, sanitized_input if sanitized_input.strip() else "(Empty notes)")
                md_preview.configure(state=tk.DISABLED)
            except Exception:
                pass

    def md_path_for_transcript(txt_path: str) -> str:
        try:
            if not txt_path:
                return ""
            folder = os.path.dirname(txt_path)
            base, _ = os.path.splitext(os.path.basename(txt_path))
            return os.path.join(folder, base + ".md")
        except Exception:
            return ""

    def do_transcribe(audio_path: str):
        try:
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"File not found: {audio_path}")

            folder = os.path.dirname(audio_path)
            file_name = os.path.basename(audio_path)
            base, _ = os.path.splitext(file_name)

            # Ensure previous stop is cleared for a new run
            try:
                stop_event.clear()
            except Exception:
                pass

            set_status("Starting transcription...")
            append_log(f"Processing file: {file_name}")

            # If this is a large video, extract/cached WAV for faster repeated runs
            cached = get_or_make_cached_wav_for_large_video(audio_path, threshold_mb=200)
            input_for_whisper = cached if cached else audio_path

            # Incremental transcription with progress + resume state
            output_file = os.path.join(folder, f"{base}.txt")
            set_status("Transcribing incrementally… writing to file as we go…")
            transcribe_incremental(input_for_whisper, output_file, chunk_sec=60, resume=True)
            append_log("Transcription completed.")

            # Update UI with result path and copy to clipboard
            out_norm = _normpath(output_file)
            output_path_var.set(out_norm)
            root.clipboard_clear()
            root.clipboard_append(out_norm)
            root.update()  # now it stays on the clipboard after the app exits

            set_status("Saved transcript and copied path to clipboard. You can select another file.")
            append_log(f"Saved transcript to: {output_file}")

            # If the file is in the current folder view, update its transcript column
            if current_folder_var.get() and os.path.dirname(audio_path) == current_folder_var.get():
                item_id = path_to_item.get(audio_path)
                if item_id:
                    tree.set(item_id, "transcript", _normpath(output_file))
                    # Auto-fit transcript column after update
                    try:
                        autofit_tree_columns(tree, cols, min_widths={"size": 80, "modified": 140}, padding=18)
                    except Exception:
                        pass

            # Optional: show a message box
            try:
                messagebox.showinfo("Transcription Saved", f"Transcript saved to:\n{output_file}\n\nPath copied to clipboard.")
            except Exception:
                # In case messagebox cannot be shown in some environments
                pass

        except FileNotFoundError as e:
            set_status("Error: Required file not found.")
            append_log(str(e))
            append_log("1) The audio file was moved or deleted\n2) FFmpeg is not properly installed")
        except Exception as e:
            set_status("Unexpected error. See log.")
            append_log(f"Unexpected error: {e}")
            append_log(traceback.format_exc())
        finally:
            # Re-enable the button
            select_btn.configure(state=tk.NORMAL, text="Select Audio")

    def on_select_audio():
        # Allow multiple selection; model is reused
        # Support common video files as well (decoded via FFmpeg for Whisper)
        paths = filedialog.askopenfilenames(
            title="Select media file(s)",
            filetypes=[
                ("Audio files", "*.mp3 *.wav *.m4a *.flac *.aac *.ogg *.wma"),
                ("Video files", "*.mp4 *.mov *.mkv *.avi *.wmv *.m4v *.webm *.mts *.m2ts *.ts *.3gp *.flv *.mpeg"),
                ("All files", "*.*"),
            ],
        )
        if not paths:
            return

        # Convert to list and normalize
        file_list = [p for p in paths if p]
        if not file_list:
            return

        # Add the parent folder of the first selected file to Recent
        try:
            first_dir = os.path.dirname(os.path.abspath(file_list[0]))
            if first_dir and os.path.isdir(first_dir):
                add_recent_folder(first_dir)
        except Exception:
            pass

        # Disable while working
        select_btn.configure(state=tk.DISABLED, text="Transcribing...")
        transcribe_sel_btn.configure(state=tk.DISABLED)

        def run_batch():
            try:
                for idx, audio_path in enumerate(file_list, start=1):
                    current_file_var.set(audio_path)
                    output_path_var.set("")
                    set_status(f"[{idx}/{len(file_list)}] Starting transcription...")
                    append_log("")

                    # Perform transcription (same settings as single)
                    try:
                        if not os.path.exists(audio_path):
                            raise FileNotFoundError(f"File not found: {audio_path}")
                        folder = os.path.dirname(audio_path)
                        file_name = os.path.basename(audio_path)
                        base, _ = os.path.splitext(file_name)

                        append_log(f"Processing file: {file_name}")
                        output_file = os.path.join(folder, f"{base}.txt")
                        set_status(f"[{idx}/{len(file_list)}] Transcribing incrementally…")
                        transcribe_incremental(audio_path, output_file, chunk_sec=60, resume=True)

                        out_norm = _normpath(output_file)
                        output_path_var.set(out_norm)
                        root.clipboard_clear()
                        root.clipboard_append(out_norm)
                        root.update()
                        set_status(f"[{idx}/{len(file_list)}] Saved transcript and copied path. Next...")
                        append_log(f"Saved transcript to: {output_file}")

                        # Update tree if folder matches current view
                        if current_folder_var.get() and os.path.dirname(audio_path) == current_folder_var.get():
                            item_id = path_to_item.get(audio_path)
                            if item_id:
                                tree.set(item_id, "transcript", _normpath(output_file))
                                try:
                                    autofit_tree_columns(tree, cols, min_widths={"size": 80, "modified": 140}, padding=18)
                                except Exception:
                                    pass
                    except RuntimeError as e:
                        if "canceled by user" in str(e).lower():
                            # Graceful stop for batch
                            set_status("Canceled by user.")
                            append_log("Batch canceled.")
                            break
                        else:
                            append_log(f"Error transcribing {audio_path}: {e}")
                            append_log(traceback.format_exc())
                            continue
                    except Exception as e:
                        append_log(f"Error transcribing {audio_path}: {e}")
                        append_log(traceback.format_exc())
                        continue
            finally:
                select_btn.configure(state=tk.NORMAL, text="Select Audio")
                transcribe_sel_btn.configure(state=tk.NORMAL)
                set_status("Batch complete.")

        threading.Thread(target=run_batch, daemon=True).start()

    def load_preview_for_item(iid: str):
        if not iid:
            set_preview_text("")
            return
        vals = tree.item(iid, "values")
        if not vals or len(vals) < 4:
            set_preview_text("")
            return
        transcript_path = vals[3]
        # Normalize and handle potential Windows long-path issues
        tp = transcript_path if isinstance(transcript_path, str) else ""
        tp = (tp or "").strip().strip('"')
        # Resolve to absolute and extended-length if necessary
        tp_resolved = _win_long_path(tp)
        if tp_resolved and isinstance(tp_resolved, str) and os.path.isfile(tp_resolved):
            try:
                with open(tp_resolved, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                set_preview_text(content)
                nb.select(preview_frame)
            except Exception as e:
                try:
                    plen = len(tp_resolved)
                except Exception:
                    plen = 0
                set_preview_text(f"Failed to load transcript:\n{e}\nPath length: {plen}\nPath: {tp_resolved}")
        else:
            # No transcript: show empty preview
            set_preview_text("")

    def load_notes_for_item(iid: str):
        # Load notes editor based on the transcript path of the selected row
        if not iid:
            current_md_path_var.set("")
            notes_editor.delete("1.0", tk.END)
            render_markdown_to_preview("")
            return
        vals = tree.item(iid, "values")
        if not vals or len(vals) < 4:
            current_md_path_var.set("")
            notes_editor.delete("1.0", tk.END)
            render_markdown_to_preview("")
            return
        transcript_path = vals[3]
        # Compute audio-based and transcript-based candidates
        audio_display = vals[0] if len(vals) > 0 else ""
        if isinstance(audio_display, str) and audio_display.startswith("🎥 "):
            audio_display = audio_display[2:].lstrip()
        base_name = audio_display.replace(" (md only)", "").replace(" (no audio)", "").strip()
        # Remove any file extension from the display-derived base to avoid names like name.mp3.md
        try:
            base_name = os.path.splitext(base_name)[0]
        except Exception:
            pass
        folder = current_folder_var.get()
        audio_md = os.path.join(folder, base_name + ".md") if folder and base_name else ""
        txt_md = md_path_for_transcript(transcript_path) if (isinstance(transcript_path, str) and transcript_path and os.path.isfile(transcript_path)) else ""

        # Choose MD to show: prefer existing audio_md, then existing txt_md; else plan to write to audio_md
        chosen_md = audio_md if (audio_md and os.path.isfile(audio_md)) else (txt_md if (txt_md and os.path.isfile(txt_md)) else audio_md)
        current_md_path_var.set(chosen_md)
        notes_editor.delete("1.0", tk.END)
        if chosen_md and os.path.isfile(chosen_md):
            try:
                with open(chosen_md, "r", encoding="utf-8", errors="replace") as f:
                    notes_editor.insert(tk.END, f.read())
            except Exception as e:
                notes_editor.insert(tk.END, f"Failed to load notes:\n{e}")
        else:
            # No markdown file: show empty notes editor
            pass
        # Update preview to match editor content
        try:
            content = notes_editor.get("1.0", tk.END)
        except Exception:
            content = ""
        render_markdown_to_preview(content)

        # Diagnostics to log selection mapping (helps investigate mismatches)
        try:
            a_disp = vals[0] if len(vals) > 0 else ""
            t_disp = transcript_path if isinstance(transcript_path, str) else ""
            append_log(f"Notes selection: audio='{a_disp}' | transcript='{t_disp}' | audio_md='{audio_md}' | txt_md='{txt_md}' | chosen='{chosen_md}'")
        except Exception:
            pass

    def on_save_notes():
        md_path = current_md_path_var.get().strip()
        if not md_path:
            # Try to derive a sensible target from the current selection
            try:
                sel = tree.selection()
                iid = sel[0] if sel else ""
            except Exception:
                iid = ""
            target_folder = (current_folder_var.get() or "").strip()
            audio_base = ""
            transcript_dir = ""
            if iid:
                try:
                    vals = tree.item(iid, "values") or []
                    audio_disp = str(vals[0]) if len(vals) > 0 else ""
                    if audio_disp.startswith("🎥 "):
                        audio_disp = audio_disp[2:].lstrip()
                    audio_base = audio_disp.replace(" (md only)", "").replace(" (no audio)", "").strip()
                    # Strip any extension so MD becomes base.md, not base.mp3.md
                    try:
                        audio_base = os.path.splitext(audio_base)[0]
                    except Exception:
                        pass
                    if len(vals) >= 4 and isinstance(vals[3], str) and os.path.isfile(vals[3]):
                        transcript_dir = os.path.dirname(vals[3])
                except Exception:
                    pass
            if not target_folder:
                target_folder = transcript_dir
            if not target_folder:
                # As a last resort, ask the user for a folder to save notes
                try:
                    target_folder = filedialog.askdirectory(title="Select folder to save notes")
                except Exception:
                    target_folder = ""
            if target_folder and audio_base:
                md_path = os.path.join(target_folder, audio_base + ".md")
                current_md_path_var.set(md_path)
            else:
                messagebox.showwarning("No target path", "Please select a row or choose a folder before saving notes.")
                return
        try:
            os.makedirs(os.path.dirname(md_path), exist_ok=True)
            content = notes_editor.get("1.0", tk.END)
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(content)
            set_status(f"Saved notes to: {md_path}")
            # Refresh preview after save
            render_markdown_to_preview(content)
            # Update saved-at label
            try:
                saved_at_var.set(f"Saved at {datetime.now().strftime('%H:%M:%S')}")
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror("Save Failed", f"Could not save notes:\n{e}")

    def on_reveal_notes():
        md_path = current_md_path_var.get().strip()
        if md_path:
            reveal_in_explorer(md_path)

    # Wire Notes toolbar buttons now that handlers are defined
    try:
        notes_save_btn.configure(command=on_save_notes)
        notes_reveal_btn.configure(command=on_reveal_notes)
    except Exception:
        pass

    # Manual auto-fit trigger
    def on_autofit_columns():
        try:
            root.update_idletasks()
            autofit_tree_columns(tree, cols, min_widths={"size": 80, "modified": 140}, padding=18)
            set_status("Columns auto-fitted.")
        except Exception:
            pass

    def on_add_md_only():
        # Ensure we have a target folder
        folder = current_folder_var.get().strip()
        if not folder or not os.path.isdir(folder):
            folder = filedialog.askdirectory(title="Select a folder to create the Markdown file")
            if not folder:
                return
            current_folder_var.set(folder)
            append_log(f"Folder selected: {folder}")

        # Prompt for base name
        base = simpledialog.askstring(
            "Add Markdown Only",
            "File base name (without extension):",
            parent=root,
        )
        if base is None:
            return
        base = base.strip()
        # Strip any trailing media or text/markdown extensions to keep MD clean
        try:
            _strip_exts = [
                ".mp3", ".wav", ".m4a", ".flac", ".aac", ".wma", ".ogg", ".opus",
                ".mp4", ".mkv", ".mov", ".avi", ".wmv", ".webm", ".m4v",
                ".txt", ".md",
            ]
            while True:
                lower = base.lower()
                matched = False
                for _ext in _strip_exts:
                    if lower.endswith(_ext):
                        base = base[: -len(_ext)]
                        matched = True
                        break
                if not matched:
                    break
            base = base.strip().rstrip('.')
        except Exception:
            pass
        invalid_chars = ['\\', '/', '\\r', '\\n', ':', '*', '?', '"', '<', '>', '|']
        if not base or any(ch in base for ch in invalid_chars):
            messagebox.showerror("Invalid name", "Please enter a valid file base name.")
            return

        md_path = os.path.join(folder, base + ".md")
        # Create or overwrite
        try:
            os.makedirs(folder, exist_ok=True)
            # Prepare images folder and a tiny placeholder image
            images_dir = os.path.join(folder, "images")
            os.makedirs(images_dir, exist_ok=True)
            placeholder_name = f"{base}.png"
            placeholder_path = os.path.join(images_dir, placeholder_name)
            # 1x1 transparent PNG
            _PNG_1x1_TRANSPARENT = (
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGMAAQAABQABDQottAAAAABJRU5ErkJggg=="
            )
            try:
                with open(placeholder_path, "wb") as imgf:
                    imgf.write(base64.b64decode(_PNG_1x1_TRANSPARENT))
            except Exception:
                # Non-fatal; continue without blocking creation
                pass
            # Write initial markdown template (with hyperlink example)
            initial = (
                f"# {base}\n\n"
                f"![Add image here](images/{placeholder_name})\n\n"
                f"Write your notes here.\n\n"
                f"## Example: Hyperlink\n"
                f"You can add a link like this: [OpenAI](https://www.openai.com).\n"
            )
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(initial)
        except Exception as e:
            messagebox.showerror("Create Failed", f"Could not create markdown file.\n\n{e}")
            return

        # Refresh UI and select the new row
        try:
            populate_tree(folder)
            add_recent_folder(folder)
            # Try to locate the inserted md-only row
            target_display = f"{base} (md only)"
            found_iid = None
            for iid in tree.get_children(""):
                vals = tree.item(iid, "values")
                if vals and len(vals) > 0 and str(vals[0]) == target_display:
                    found_iid = iid
                    break
            if found_iid:
                tree.focus(found_iid)
                tree.selection_set(found_iid)
                nb.select(notes_frame)
                # Load notes editor to this md file
                current_md_path_var.set(md_path)
                try:
                    notes_editor.delete("1.0", tk.END)
                    with open(md_path, "r", encoding="utf-8", errors="replace") as f:
                        notes_editor.insert(tk.END, f.read())
                except Exception:
                    pass
                # Render preview too
                try:
                    content = notes_editor.get("1.0", tk.END)
                except Exception:
                    content = ""
                render_markdown_to_preview(content)
            set_status(f"Created notes: {md_path}")
        except Exception:
            pass

    # Transcribe directly from a URL (e.g., YouTube) by downloading audio first
    def on_transcribe_url():
        try:
            # Ask for URL
            url = simpledialog.askstring(
                "Transcribe URL",
                "Enter media URL (YouTube, etc.):",
                parent=root,
            )
            if not url:
                return

            # Choose destination folder for transcript
            dest_folder = current_folder_var.get().strip()
            if not dest_folder or not os.path.isdir(dest_folder):
                dest_folder = filedialog.askdirectory(title="Select a folder to save the transcript")
                if not dest_folder:
                    return
                current_folder_var.set(dest_folder)
                append_log(f"Folder selected: {dest_folder}")
            # Add to Recent
            try:
                add_recent_folder(dest_folder)
            except Exception:
                pass

            # Disable buttons while we work
            try:
                transcribe_url_btn.configure(state=tk.DISABLED, text="Downloading...")
                select_btn.configure(state=tk.DISABLED)
                transcribe_sel_btn.configure(state=tk.DISABLED)
            except Exception:
                pass

            def worker():
                temp_dir = None
                media_path = None
                try:
                    set_status("Downloading media...")
                    media_path, temp_dir = _download_media_to_temp(url)
                    if not media_path:
                        set_status("Download failed. See log.")
                        return

                    # Determine base name to use for output
                    file_name = os.path.basename(media_path)
                    base, _ = os.path.splitext(file_name)

                    append_log(f"Processing URL → file: {file_name}")
                    set_status("Transcribing...")

                    # Run Whisper directly so we can control the destination folder
                    try:
                        # Optionally extract cached WAV for large video files
                        cached = get_or_make_cached_wav_for_large_video(media_path, threshold_mb=200)
                    except Exception:
                        cached = None
                    input_for_whisper = cached if cached else media_path

                    args = compute_transcribe_args()
                    output_file = os.path.join(dest_folder, f"{base}.txt")
                    set_status("Transcribing incrementally… writing to file as we go…")
                    transcribe_incremental(input_for_whisper, output_file, chunk_sec=60)
                    append_log("Transcription completed.")

                    out_norm = _normpath(output_file)
                    output_path_var.set(out_norm)
                    try:
                        root.clipboard_clear()
                        root.clipboard_append(out_norm)
                        root.update()
                    except Exception:
                        pass

                    set_status("Saved transcript and copied path to clipboard.")
                    append_log(f"Saved transcript to: {output_file}")

                    # If the destination matches current view, refresh and try to reflect transcript
                    try:
                        if current_folder_var.get() and os.path.abspath(dest_folder) == os.path.abspath(current_folder_var.get()):
                            populate_tree(dest_folder)
                            # Attempt to locate the just-saved transcript row to show preview
                            for iid in tree.get_children(""):
                                vals = tree.item(iid, "values")
                                if vals and len(vals) > 3 and str(vals[3]) == out_norm:
                                    tree.focus(iid)
                                    tree.selection_set(iid)
                                    nb.select(preview_frame)
                                    break
                    except Exception:
                        pass
                except Exception as e:
                    append_log(f"URL transcription failed: {e}")
                    append_log(traceback.format_exc())
                    set_status("Unexpected error. See log.")
                finally:
                    # Cleanup temp dir
                    try:
                        if temp_dir and os.path.isdir(temp_dir):
                            shutil.rmtree(temp_dir, ignore_errors=True)
                    except Exception:
                        pass
                    # Re-enable buttons
                    try:
                        transcribe_url_btn.configure(state=tk.NORMAL, text="Transcribe URL")
                        select_btn.configure(state=tk.NORMAL)
                        transcribe_sel_btn.configure(state=tk.NORMAL)
                    except Exception:
                        pass

            threading.Thread(target=worker, daemon=True).start()
        except Exception:
            # Non-fatal UI errors
            pass

    # Sorting state and helper
    sort_state = {}

    def tree_sort_by(col: str):
        # Toggle sort order for the column
        reverse = sort_state.get(col, False)
        items = list(tree.get_children(""))

        def key_for(iid):
            vals = tree.item(iid, "values")
            if not vals:
                return ""
            if col == "audio":
                return (vals[0] or "").lower()
            elif col == "size":
                folder = current_folder_var.get()
                try:
                    return os.path.getsize(os.path.join(folder, vals[0]))
                except Exception:
                    return -1
            elif col == "modified":
                folder = current_folder_var.get()
                try:
                    return os.path.getmtime(os.path.join(folder, vals[0]))
                except Exception:
                    return 0.0
            elif col == "transcript":
                return (vals[3] if len(vals) > 3 else "").lower()
            elif col == "txt_size":
                try:
                    return int(vals[4]) if len(vals) > 4 and str(vals[4]).strip().isdigit() else 0
                except Exception:
                    return 0
            elif col == "md_size":
                try:
                    return int(vals[5]) if len(vals) > 5 and str(vals[5]).strip().isdigit() else 0
                except Exception:
                    return 0
            return (vals[0] or "").lower()

        items.sort(key=key_for, reverse=reverse)
        for idx, iid in enumerate(items):
            tree.move(iid, "", idx)
        # Update indicator on headers
        current_ascending = not reverse
        for c in cols:
            label = header_labels.get(c, c)
            if c == col:
                indicator = " ▲" if current_ascending else " ▼"
                tree.heading(c, text=label + indicator, command=lambda cc=c: tree_sort_by(cc))
            else:
                tree.heading(c, text=label, command=lambda cc=c: tree_sort_by(cc))
        sort_state[col] = not reverse
        # Auto-fit to account for header indicator and any content impact
        try:
            autofit_tree_columns(tree, cols, min_widths={"size": 80, "modified": 140}, padding=18)
        except Exception:
            pass

    def populate_tree(folder: str):
        # Clear existing view and model
        try:
            for iid in tree.get_children():
                tree.delete(iid)
        except Exception:
            pass
        path_to_item.clear()
        all_entries.clear()

        if not folder or not os.path.isdir(folder):
            return

        # Treat common video extensions as transcribable media (audio extracted by FFmpeg)
        audio_exts = {
            ".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg", ".wma",
            ".mp4", ".mov", ".mkv", ".avi", ".wmv", ".m4v", ".webm", ".mts", ".m2ts", ".ts",
            ".3gp", ".flv", ".mpeg",
        }
        entries = []
        audio_bases = set()
        names = sorted(os.listdir(folder))
        # First, collect audio/video files
        for name in names:
            full = os.path.join(folder, name)
            if not os.path.isfile(full):
                continue
            base, ext = os.path.splitext(name)
            if ext.lower() in audio_exts:
                audio_bases.add(base)
                txt_path = os.path.join(folder, base + ".txt")
                transcript = _normpath(txt_path) if os.path.exists(txt_path) else "(missing)"
                # sizes for txt/md
                try:
                    txt_size_b = os.path.getsize(txt_path) if os.path.isfile(txt_path) else 0
                except Exception:
                    txt_size_b = 0
                try:
                    md_path = md_path_for_transcript(txt_path)
                    md_size_b = os.path.getsize(md_path) if (md_path and os.path.isfile(md_path)) else 0
                except Exception:
                    md_size_b = 0

                try:
                    size_bytes = os.path.getsize(full)
                except Exception:
                    size_bytes = 0
                try:
                    mtime = os.path.getmtime(full)
                except Exception:
                    mtime = 0.0
                size_str = human_readable_size(size_bytes)
                modified_str = human_readable_mtime(mtime)
                display_name = ("🎥 " + name) if is_video_file(full) else name
                entries.append((display_name, full, size_str, modified_str, transcript, True, str(txt_size_b), str(md_size_b)))

        # Then, include standalone .txt transcripts without audio
        for name in names:
            full = os.path.join(folder, name)
            if not os.path.isfile(full):
                continue
            base, ext = os.path.splitext(name)
            if ext.lower() == ".txt" and base not in audio_bases:
                # Represent as "<base> (no audio)" in the audio column
                display_audio_name = f"{base} (no audio)"
                try:
                    size_bytes = os.path.getsize(full)
                except Exception:
                    size_bytes = 0
                try:
                    mtime = os.path.getmtime(full)
                except Exception:
                    mtime = 0.0
                size_str = human_readable_size(size_bytes)
                modified_str = human_readable_mtime(mtime)
                transcript = _normpath(full)  # the .txt file path
                # sizes for txt/md
                txt_size_b = size_bytes
                try:
                    md_path = md_path_for_transcript(full)
                    md_size_b = os.path.getsize(md_path) if (md_path and os.path.isfile(md_path)) else 0
                except Exception:
                    md_size_b = 0
                # Use a placeholder full path for mapping? We skip mapping since there's no audio
                entries.append((display_audio_name, None, size_str, modified_str, transcript, False, str(txt_size_b), str(md_size_b)))

        # Finally, include standalone .md notes without audio/.txt
        for name in names:
            full = os.path.join(folder, name)
            if not os.path.isfile(full):
                continue
            base, ext = os.path.splitext(name)
            if ext.lower() == ".md" and base not in audio_bases:
                # Only include if there's no .txt alongside (pure md-only case)
                if not os.path.isfile(os.path.join(folder, base + ".txt")):
                    display_audio_name = f"{base} (md only)"
                    try:
                        size_bytes = os.path.getsize(full)
                    except Exception:
                        size_bytes = 0
                    try:
                        mtime = os.path.getmtime(full)
                    except Exception:
                        mtime = 0.0
                    size_str = human_readable_size(size_bytes)
                    modified_str = human_readable_mtime(mtime)
                    transcript = "(missing)"  # no transcript .txt
                    # sizes for txt/md
                    txt_size_b = 0
                    md_size_b = size_bytes
                    entries.append((display_audio_name, None, size_str, modified_str, transcript, False, str(txt_size_b), str(md_size_b)))

        # Update model and render via filter
        try:
            all_entries.extend(entries)
        except Exception:
            # Fallback: still show current entries
            for e in entries:
                all_entries.append(e)
        apply_filter()

    def on_browse_folder():
        folder = filedialog.askdirectory(title="Select a folder of audio files")
        if not folder:
            return
        current_folder_var.set(folder)
        append_log(f"Folder selected: {folder}")
        populate_tree(folder)
        add_recent_folder(folder)
        try:
            save_last_folder(folder)
        except Exception:
            pass

    def _update_status_for_selection(iid: str | None):
        try:
            if not iid:
                return
            vals = tree.item(iid, "values")
            if not vals:
                return
            sel_name = str(vals[0]) if len(vals) > 0 else ""
            # Only update the current file portion; keep the rest via status_var
            current_file_var.set(sel_name)
        except Exception:
            pass

    def _derive_md_path_from_row(iid: str) -> str:
        try:
            vals = tree.item(iid, "values") or []
            if len(vals) < 1:
                return ""
            # Derive audio-based candidate from display name and current folder
            audio_display = str(vals[0])
            # Strip UI adornments: video emoji and special suffixes
            if audio_display.startswith("🎥 "):
                audio_display = audio_display[2:].lstrip()
            base_name = audio_display.replace(" (md only)", "").replace(" (no audio)", "").strip()
            # Ensure we don't carry media extensions into the Markdown filename
            try:
                base_name = os.path.splitext(base_name)[0]
            except Exception:
                pass
            folder = current_folder_var.get().strip()
            audio_md = os.path.join(folder, base_name + ".md") if (folder and base_name) else ""

            # Transcript-based candidate
            txt_path = vals[3] if len(vals) >= 4 else ""
            txt_md = md_path_for_transcript(txt_path) if (isinstance(txt_path, str) and os.path.isfile(txt_path)) else ""

            # Prefer existing audio-based MD; else existing transcript-based MD
            if audio_md and os.path.isfile(audio_md):
                return audio_md
            if txt_md and os.path.isfile(txt_md):
                return txt_md
            # If neither exists, return audio-based target (for future saves)
            return audio_md or txt_md or ""
        except Exception:
            pass
        return ""

    def on_tree_select(event):
        try:
            sel = tree.selection()
            if not sel:
                return
            iid = sel[0]
            # Update status bar current file portion
            _update_status_for_selection(iid)

            # Determine preferred display: Markdown > TXT > Log
            md_path = _derive_md_path_from_row(iid)
            if md_path and os.path.isfile(md_path):
                # Load notes editor + preview, switch to Notes tab
                load_notes_for_item(iid)
                try:
                    nb.select(notes_frame)
                except Exception:
                    pass
                return

            # Fallback to transcript preview if present
            vals = tree.item(iid, "values") or []
            txt_path = str(vals[3]) if len(vals) >= 4 else ""
            if txt_path and os.path.isfile(txt_path):
                load_preview_for_item(iid)
                # Clear Notes context to avoid showing stale markdown from previous selection
                try:
                    current_md_path_var.set("")
                    notes_editor.delete("1.0", tk.END)
                    # Also clear the Markdown preview explicitly since there is no .md for this row
                    render_markdown_to_preview("")
                except Exception:
                    pass
                try:
                    nb.select(preview_frame)
                except Exception:
                    pass
                return

            # Otherwise, show Log tab
            try:
                # Also clear Notes context for rows without md/txt
                current_md_path_var.set("")
                notes_editor.delete("1.0", tk.END)
                # Clear the Markdown preview explicitly since there is no .md for this row
                render_markdown_to_preview("")
            except Exception:
                pass
            try:
                nb.select(log_frame)
            except Exception:
                pass
        except Exception:
            pass

    def on_tree_double_click(event):
        item = tree.focus()
        if not item:
            return
        values = tree.item(item, "values")
        if not values:
            return
        audio_name = values[0]
        folder = current_folder_var.get()
        if not folder:
            return
        audio_path = os.path.join(folder, display_to_real_filename(audio_name))
        current_file_var.set(audio_path)
        output_path_var.set("")
        set_status("Preparing transcription...")
        select_btn.configure(state=tk.DISABLED, text="Transcribing...")
        t = threading.Thread(target=do_transcribe, args=(audio_path,), daemon=True)
        t.start()

    def on_transcribe_selected():
        # Transcribe all selected rows in the visual order
        sel = list(tree.selection())
        if not sel:
            messagebox.showwarning("No selection", "Please select one or more audio files in the list.")
            return
        folder = current_folder_var.get()
        if not folder:
            return
        # Order selected items by their current display order
        order = []
        selected_set = set(sel)
        for iid in tree.get_children(""):
            if iid in selected_set:
                order.append(iid)

        file_list = []
        for iid in order:
            vals = tree.item(iid, "values")
            if vals:
                file_list.append(os.path.join(folder, display_to_real_filename(vals[0])))
        if not file_list:
            return

        # Disable while working
        select_btn.configure(state=tk.DISABLED)
        transcribe_sel_btn.configure(state=tk.DISABLED, text="Transcribing...")

        def run_batch():
            try:
                for idx, audio_path in enumerate(file_list, start=1):
                    current_file_var.set(audio_path)
                    output_path_var.set("")
                    set_status(f"[{idx}/{len(file_list)}] Starting transcription...")
                    append_log("")
                    try:
                        if not os.path.exists(audio_path):
                            raise FileNotFoundError(f"File not found: {audio_path}")
                        folder_local = os.path.dirname(audio_path)
                        file_name = os.path.basename(audio_path)
                        base, _ = os.path.splitext(file_name)
                        append_log(f"Processing file: {file_name}")
                        cached = get_or_make_cached_wav_for_large_video(audio_path, threshold_mb=200)
                        input_for_whisper = cached if cached else audio_path
                        output_file = os.path.join(folder_local, f"{base}.txt")
                        set_status(f"[{idx}/{len(file_list)}] Transcribing incrementally…")
                        transcribe_incremental(input_for_whisper, output_file, chunk_sec=60)
                        output_path_var.set(output_file)
                        root.clipboard_clear()
                        root.clipboard_append(output_file)
                        root.update()
                        set_status(f"[{idx}/{len(file_list)}] Saved transcript and copied path. Next...")
                        append_log(f"Saved transcript to: {output_file}")
                        # Update row
                        item_id = path_to_item.get(audio_path)
                        if item_id:
                            tree.set(item_id, "transcript", output_file)
                    except Exception as e:
                        append_log(f"Error transcribing {audio_path}: {e}")
                        append_log(traceback.format_exc())
                        continue
            finally:
                select_btn.configure(state=tk.NORMAL)
                transcribe_sel_btn.configure(state=tk.NORMAL, text="Transcribe Selected")
                set_status("Batch complete.")

        threading.Thread(target=run_batch, daemon=True).start()

    # --- Right-click menu for the transcript entry ---
    entry_menu = tk.Menu(root, tearoff=0)
    def entry_copy_full_path():
        path = output_path_var.get().strip()
        if path:
            copy_to_clipboard(path)
            set_status("Copied full path to clipboard.")
    def entry_copy_file_name():
        path = output_path_var.get().strip()
        if path:
            copy_to_clipboard(os.path.basename(path))
            set_status("Copied file name to clipboard.")
    def entry_reveal():
        path = output_path_var.get().strip()
        if path:
            reveal_in_explorer(path)

    entry_menu.add_command(label="Copy Full Path", command=entry_copy_full_path)
    entry_menu.add_command(label="Copy File Name", command=entry_copy_file_name)
    def entry_copy_folder_path():
        path = output_path_var.get().strip()
        if path:
            copy_to_clipboard(os.path.dirname(path))
            set_status("Copied folder path to clipboard.")
    def entry_open():
        path = output_path_var.get().strip()
        if path and os.path.isfile(path):
            open_with_default_app(path)

    entry_menu.add_separator()
    entry_menu.add_command(label="Copy Folder Path", command=entry_copy_folder_path)
    entry_menu.add_command(label="Open Transcript", command=entry_open)
    entry_menu.add_command(label="Reveal in Explorer", command=entry_reveal)

    def show_entry_menu(event):
        try:
            entry_menu.tk_popup(event.x_root, event.y_root)
        finally:
            entry_menu.grab_release()

    out_entry.bind("<Button-3>", show_entry_menu)  # Right-click on Windows

    # --- Audio Extraction Utilities ---
    def _expected_extracted_wav_for(media_path: str) -> str:
        try:
            folder = os.path.dirname(media_path)
            base, _ = os.path.splitext(os.path.basename(media_path))
            return os.path.join(folder, f"{base}.wav")
        except Exception:
            return ""

    def _probe_audio_streams(input_path: str) -> list:
        """Return a list of audio stream metadata using ffprobe. Each item includes
        position (0-based among audio streams), index, channels, bitrate, language, codec_name.
        """
        try:
            import json as _json
            # Prefer ffprobe; if missing, try ffprobe.exe explicitly (Windows)
            probe_cmd = _resolve_ffprobe_cmd()
            cmd = [
                probe_cmd, "-v", "error",
                "-select_streams", "a",
                "-show_entries", "stream=index,channels,codec_name,channel_layout,bit_rate:stream_tags=language",
                "-of", "json",
                input_path,
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                try:
                    append_log(f"ffprobe failed (code {res.returncode}). Streams unavailable.\n{res.stderr[:400] if res.stderr else ''}")
                except Exception:
                    pass
                return []
            data = _json.loads(res.stdout or "{}")
            streams = data.get("streams", [])
            items = []
            for pos, s in enumerate(streams):
                try:
                    items.append({
                        "pos": pos,
                        "index": int(s.get("index", pos)),
                        "channels": int(s.get("channels", 0) or 0),
                        "bit_rate": int(s.get("bit_rate", 0) or 0),
                        "language": str((s.get("tags", {}) or {}).get("language", "")).lower(),
                        "codec_name": s.get("codec_name", ""),
                    })
                except Exception:
                    pass
            # Prefer more channels, then higher bitrate, prefer english/und
            def _lang_rank(lang: str) -> int:
                if lang in ("eng", "en", ""): return 2
                if lang in ("und", "undetermined"): return 1
                return 0
            items.sort(key=lambda x: (x.get("channels", 0), x.get("bit_rate", 0), _lang_rank(x.get("language", ""))), reverse=True)
            return items
        except FileNotFoundError:
            try:
                append_log("ffprobe not found on PATH. Stream dropdown will show only 'Auto'.")
            except Exception:
                pass
            return []
        except Exception as e:
            try:
                append_log(f"Stream probe error: {e}")
            except Exception:
                pass
            return []

    def extract_audio_to_wav(input_path: str, out_path: str, force_pos: int | None = None) -> bool:
        """Extract mono 16 kHz WAV from a specific/best audio stream.
        - Uses ffprobe to pick the best audio stream (by channels/bitrate/language).
        - Falls back across candidates if the result looks invalid.
        - Returns True on success.
        """
        try:
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
        except Exception:
            pass
        # Build candidate list of audio streams
        candidates = _probe_audio_streams(input_path)
        if not candidates:
            # Try default mapping as a last resort
            candidates = [{"pos": 0}]

        if force_pos is not None:
            # Only try the forced position first
            candidates = [{"pos": int(force_pos)}] + [c for c in candidates if int(c.get("pos", -1)) != int(force_pos)]

        ffmpeg_cmd = _resolve_ffmpeg_cmd()
        for c in candidates:
            pos = int(c.get("pos", 0))
            # Try multiple filter strategies to preserve audible content from multichannel sources
            # Prefer stereo first (matches Preview behavior), then mono mixes
            # 1) Stereo (no downmix) → Whisper can handle stereo
            # 2) Robust mono pan
            # 3) Simple mono pan
            filter_strategies = [
                ("stereo", [
                    "-ac", "2",
                ]),
                ("mono_robust", [
                    "-af", "pan=mono|c0=0.6*FL+0.6*FR+0.8*FC+0.4*BL+0.4*BR+0.3*LFE",
                    "-ac", "1",
                ]),
                ("mono_simple", [
                    "-af", "pan=mono|c0=0.5*FL+0.5*FR",
                    "-ac", "1",
                ]),
            ]

            for label, filt_args in filter_strategies:
                cmd = [
                    ffmpeg_cmd, "-y", "-i", input_path,
                    "-map", f"0:a:{pos}",  # pick a specific audio stream by position
                    "-vn",
                ] + filt_args + [
                    "-ar", "16000",
                    "-acodec", "pcm_s16le",  # explicit linear PCM
                    out_path,
                ]
                try:
                    try:
                        append_log(f"Trying {label} mapping for stream a:{pos}…")
                    except Exception:
                        pass
                    # Capture stderr for diagnostics
                    p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
                    _current_ffmpeg_proc["proc"] = p
                    stderr_output = ""
                    while True:
                        if stop_event.is_set():
                            try:
                                p.terminate()
                            except Exception:
                                pass
                            return False
                        rc = p.poll()
                        if rc is None:
                            root.update_idletasks(); root.update()
                            continue
                        # Process finished, collect stderr
                        try:
                            _, err = p.communicate(timeout=1)
                            if err:
                                stderr_output += err
                        except Exception:
                            pass
                        break
                    _current_ffmpeg_proc["proc"] = None
                    if rc == 0 and os.path.isfile(out_path):
                        dur = _probe_duration_seconds(out_path)
                        if dur > 0.5:
                            try:
                                append_log(f"Extracted stream a:{pos} using {label} mapping → {os.path.basename(out_path)} ({dur:.1f}s)")
                            except Exception:
                                pass
                            return True
                    # Log the error if extraction failed
                    if stderr_output:
                        try:
                            append_log(f"ffmpeg {label} error: {stderr_output[:1000]}")
                        except Exception:
                            pass
                except FileNotFoundError as e:
                    try:
                        append_log(f"ffmpeg not found: {e}. Ensure FFmpeg is installed and on PATH.")
                    except Exception:
                        pass
                    _current_ffmpeg_proc["proc"] = None
                    continue
                except Exception as e:
                    try:
                        append_log(f"ffmpeg extraction failed for {label}: {e}")
                    except Exception:
                        pass
                    _current_ffmpeg_proc["proc"] = None
                    continue

        append_log("FFmpeg extraction produced an invalid/empty WAV. Try a different input or check streams.")
        return False

    def _populate_stream_combo_for(media_path: str):
        """Populate the audio_stream_combo with streams for the given media file."""
        try:
            items = ["Auto"]
            audio_stream_map.clear(); audio_stream_map["Auto"] = None
            streams = _probe_audio_streams(media_path)
            try:
                append_log(f"Detected {len(streams)} audio stream(s) for: {os.path.basename(media_path)}")
            except Exception:
                pass
            for s in streams:
                pos = s.get("pos", 0)
                ch = s.get("channels", 0)
                br = s.get("bit_rate", 0)
                lang = (s.get("language") or "").upper()
                codec = s.get("codec_name") or ""
                br_k = f"{int(br/1000)} kbps" if br else "? kbps"
                label = f"a:{pos} — {ch}ch {br_k} ({lang or 'UND'}, {codec})"
                items.append(label)
                audio_stream_map[label] = int(pos)
            try:
                if len(items) > 1:
                    append_log("Streams: " + "; ".join(items[1:]))
                else:
                    append_log("No audio streams detected; dropdown will remain 'Auto'.")
            except Exception:
                pass
            audio_stream_combo.configure(values=items)
            try:
                # keep previous selection if valid
                cur = audio_stream_choice_var.get()
                if cur not in items:
                    audio_stream_choice_var.set("Auto")
            except Exception:
                pass
        except Exception:
            audio_stream_combo.configure(values=["Auto"])
            audio_stream_choice_var.set("Auto")

    def _selected_audio_stream_pos() -> int | None:
        try:
            key = audio_stream_choice_var.get()
            return audio_stream_map.get(key)
        except Exception:
            return None

    # --- Remux (stream copy) utilities ---
    def _expected_remux_path(media_path: str) -> str:
        try:
            folder = os.path.dirname(media_path)
            base, ext = os.path.splitext(os.path.basename(media_path))
            # Preserve extension when reasonable; default to .mp4
            out_ext = ext if ext.lower() in (".mp4", ".mkv", ".mov", ".m4a") else ".mp4"
            return os.path.join(folder, f"{base}.remux{out_ext}")
        except Exception:
            return media_path + ".remux.mp4"

    def remux_media(input_path: str, out_path: str) -> bool:
        """Container-level remux: copy all streams without re-encoding and move moov to front.
        Returns True on success and if output seems valid (>0.5s when probed).
        """
        try:
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
        except Exception:
            pass
        ffmpeg_cmd = _resolve_ffmpeg_cmd()
        cmd = [
            ffmpeg_cmd, "-y", "-i", input_path,
            "-map", "0",
            "-c", "copy",
            "-movflags", "+faststart",
            out_path,
        ]
        try:
            # Capture stderr for diagnostics
            p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
            _current_ffmpeg_proc["proc"] = p
            stderr_output = ""
            while True:
                if stop_event.is_set():
                    try:
                        p.terminate()
                    except Exception:
                        pass
                    return False
                rc = p.poll()
                if rc is None:
                    root.update_idletasks(); root.update()
                    continue
                # Process finished, collect stderr
                try:
                    _, err = p.communicate(timeout=1)
                    if err:
                        stderr_output += err
                except Exception:
                    pass
                break
            _current_ffmpeg_proc["proc"] = None
            if rc != 0 and stderr_output:
                try:
                    append_log(f"ffmpeg remux error: {stderr_output[:500]}")
                except Exception:
                    pass
            if rc == 0 and os.path.isfile(out_path):
                dur = _probe_duration_seconds(out_path)
                return dur > 0.5
            return False
        except FileNotFoundError as e:
            try:
                append_log(f"ffmpeg not found for remux: {e}. Ensure FFmpeg is installed and on PATH.")
            except Exception:
                pass
            _current_ffmpeg_proc["proc"] = None
            return False
        except Exception as e:
            try:
                append_log(f"ffmpeg remux failed: {e}")
            except Exception:
                pass
            _current_ffmpeg_proc["proc"] = None
            return False

    def on_remux_selected():
        sel = list(tree.selection())
        if not sel:
            messagebox.showwarning("No selection", "Please select one or more media files in the list.")
            return
        folder = current_folder_var.get()
        if not folder:
            return
        stop_event.clear()
        remux_btn.configure(state=tk.DISABLED, text="Remuxing…")
        set_status("Remuxing selected media…")

        def worker():
            try:
                order = []
                selected_set = set(sel)
                for iid in tree.get_children(""):
                    if iid in selected_set:
                        order.append(iid)
                for idx, iid in enumerate(order, start=1):
                    if stop_event.is_set():
                        break
                    vals = tree.item(iid, "values") or []
                    if not vals:
                        continue
                    media_path = os.path.join(folder, display_to_real_filename(vals[0]))
                    out_path = _expected_remux_path(media_path)
                    try:
                        append_log(f"[{idx}/{len(order)}] Remuxing: {os.path.basename(media_path)} → {os.path.basename(out_path)}")
                    except Exception:
                        pass
                    ok = remux_media(media_path, out_path)
                    if ok:
                        try:
                            append_log(f"Saved remux: {out_path}")
                            copy_to_clipboard(out_path)
                        except Exception:
                            pass
                    else:
                        append_log(f"Remux failed or produced invalid output: {media_path}")
                set_status("Remux complete.")
            finally:
                try:
                    remux_btn.configure(state=tk.NORMAL, text="Remux Selected")
                except Exception:
                    pass

        threading.Thread(target=worker, daemon=True).start()

    try:
        remux_btn.configure(command=on_remux_selected)
    except Exception:
        pass

    def on_extract_audio_selected():
        sel = list(tree.selection())
        if not sel:
            messagebox.showwarning("No selection", "Please select one or more media files in the list.")
            return
        folder = current_folder_var.get()
        if not folder:
            return
        stop_event.clear()
        extract_only_btn.configure(state=tk.DISABLED, text="Extracting…")
        set_status("Extracting audio…")

        def worker():
            try:
                order = []
                selected_set = set(sel)
                for iid in tree.get_children(""):
                    if iid in selected_set:
                        order.append(iid)
                chosen_pos = _selected_audio_stream_pos()
                for idx, iid in enumerate(order, start=1):
                    if stop_event.is_set():
                        break
                    vals = tree.item(iid, "values") or []
                    if not vals:
                        continue
                    media_path = os.path.join(folder, display_to_real_filename(vals[0]))
                    out_wav = _expected_extracted_wav_for(media_path)
                    append_log(f"[{idx}/{len(order)}] Extracting: {os.path.basename(media_path)} → {os.path.basename(out_wav)}")
                    ok = extract_audio_to_wav(media_path, out_wav, force_pos=chosen_pos)
                    if ok:
                        append_log(f"Saved: {out_wav}")
                        # Copy path to clipboard for convenience
                        try:
                            copy_to_clipboard(out_wav)
                        except Exception:
                            pass
                    else:
                        append_log(f"Skipped/Failed: {media_path}")
                set_status("Extraction complete.")
            finally:
                try:
                    extract_only_btn.configure(state=tk.NORMAL, text="Extract Audio Only")
                except Exception:
                    pass

        threading.Thread(target=worker, daemon=True).start()

    def on_preview_stream():
        # Preview currently selected stream on the focused row by extracting ~20s clip
        try:
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("No selection", "Select a media row to preview.")
                return
            iid = sel[0]
            vals = tree.item(iid, "values") or []
            if not vals:
                return
            folder = current_folder_var.get() or ""
            media_path = os.path.join(folder, display_to_real_filename(vals[0]))
            pos = _selected_audio_stream_pos()
            # Build a temp preview wav
            tmp_dir = tempfile.gettempdir()
            base = os.path.splitext(os.path.basename(media_path))[0]
            preview_wav = os.path.join(tmp_dir, f"{base}_preview.wav")
            # Extract first ~20 seconds for quick listening
            cmd = [
                "ffmpeg", "-y", "-i", media_path,
                *( ["-map", f"0:a:{pos}"] if pos is not None else [] ),
                "-vn", "-t", "20", "-ac", "2", "-ar", "44100", "-acodec", "pcm_s16le",
                preview_wav,
            ]
            try:
                p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                _current_ffmpeg_proc["proc"] = p
                while True:
                    if stop_event.is_set():
                        try:
                            p.terminate()
                        except Exception:
                            pass
                        return
                    rc = p.poll()
                    if rc is None:
                        root.update_idletasks(); root.update()
                        continue
                    break
                _current_ffmpeg_proc["proc"] = None
                if rc == 0 and os.path.isfile(preview_wav):
                    open_with_default_app(preview_wav)
                else:
                    messagebox.showerror("Preview failed", "Could not generate preview clip.")
            except Exception as e:
                _current_ffmpeg_proc["proc"] = None
                messagebox.showerror("Preview failed", str(e))
        except Exception:
            pass

    def on_transcribe_extracted_selected():
        sel = list(tree.selection())
        if not sel:
            messagebox.showwarning("No selection", "Please select one or more media files in the list.")
            return
        folder = current_folder_var.get()
        if not folder:
            return
        stop_event.clear()
        transcribe_extracted_btn.configure(state=tk.DISABLED, text="Transcribing…")
        set_status("Transcribing extracted audio…")

        def run_batch():
            try:
                order = []
                selected_set = set(sel)
                for iid in tree.get_children(""):
                    if iid in selected_set:
                        order.append(iid)
                for idx, iid in enumerate(order, start=1):
                    if stop_event.is_set():
                        break
                    vals = tree.item(iid, "values") or []
                    if not vals:
                        continue
                    media_path = os.path.join(folder, display_to_real_filename(vals[0]))
                    wav_path = _expected_extracted_wav_for(media_path)
                    if not os.path.isfile(wav_path):
                        append_log(f"No extracted WAV found for: {os.path.basename(media_path)}; expected {os.path.basename(wav_path)}. Run 'Extract Audio Only' first.")
                        continue
                    # Perform standard do_transcribe() but feed the wav_path
                    try:
                        current_file_var.set(wav_path)
                        output_path_var.set("")
                        set_status(f"[{idx}/{len(order)}] Transcribing extracted audio…")
                        append_log(f"Processing extracted audio: {os.path.basename(wav_path)}")
                        args = compute_transcribe_args()
                        if stop_event.is_set():
                            break
                        folder_local = os.path.dirname(media_path)
                        base, _ = os.path.splitext(os.path.basename(media_path))
                        output_file = os.path.join(folder_local, f"{base}.txt")
                        set_status(f"[{idx}/{len(order)}] Transcribing incrementally…")
                        transcribe_incremental(wav_path, output_file, chunk_sec=60, resume=True)
                        output_path_var.set(output_file)
                        try:
                            root.clipboard_clear(); root.clipboard_append(output_file); root.update()
                        except Exception:
                            pass
                        set_status(f"[{idx}/{len(order)}] Saved transcript and copied path. Next…")
                        append_log(f"Saved transcript to: {output_file}")
                        # Update row transcript column
                        item_id = path_to_item.get(media_path)
                        if item_id:
                            tree.set(item_id, "transcript", output_file)
                    except RuntimeError as e:
                        if "canceled by user" in str(e).lower():
                            set_status("Canceled by user.")
                            append_log("Transcription canceled.")
                            break
                        else:
                            append_log(f"Error transcribing extracted audio for {media_path}: {e}")
                            append_log(traceback.format_exc())
                            continue
                    except Exception as e:
                        append_log(f"Error transcribing extracted audio for {media_path}: {e}")
                        append_log(traceback.format_exc())
                        continue
            finally:
                try:
                    transcribe_extracted_btn.configure(state=tk.NORMAL, text="Transcribe Extracted")
                except Exception:
                    pass
                set_status("Done.")

        threading.Thread(target=run_batch, daemon=True).start()

    # Wire up new buttons
    try:
        extract_only_btn.configure(command=on_extract_audio_selected)
        transcribe_extracted_btn.configure(command=on_transcribe_extracted_selected)
        preview_stream_btn.configure(command=on_preview_stream)
        refresh_streams_btn.configure(command=lambda: _refresh_streams_for_selection())
    except Exception:
        pass

    # When selection changes, refresh the stream list for that file
    def _refresh_streams_for_selection():
        try:
            sel = tree.selection()
            if not sel:
                audio_stream_combo.configure(values=["Auto"])
                audio_stream_choice_var.set("Auto")
                return
            iid = sel[0]
            vals = tree.item(iid, "values") or []
            if not vals:
                return
            folder = current_folder_var.get() or ""
            media_path = os.path.join(folder, display_to_real_filename(vals[0]))
            _populate_stream_combo_for(media_path)
        except Exception:
            pass

    try:
        tree.bind("<<TreeviewSelect>>", lambda e: (_refresh_streams_for_selection(), on_tree_select(e)))
    except Exception:
        pass

    # --- Right-click menu for the file list (uses transcript column) ---
    tree_menu = tk.Menu(root, tearoff=0)
    def tree_get_selected_paths():
        item = tree.focus()
        if not item:
            return None, None
        vals = tree.item(item, "values")
        if not vals:
            return None, None
        # vals: [audio_name, size_str, modified_str, transcript_val]
        audio_name = vals[0]
        transcript_val = vals[3] if len(vals) > 3 else None
        folder = current_folder_var.get()
        audio_path = os.path.join(folder, display_to_real_filename(audio_name)) if folder else None
        transcript_path = transcript_val if transcript_val and transcript_val != "(missing)" else None
        return audio_path, transcript_path

    def tree_copy_full_path():
        _, transcript_path = tree_get_selected_paths()
        if transcript_path:
            copy_to_clipboard(transcript_path)
            set_status("Copied transcript full path to clipboard.")

    def tree_copy_file_name():
        _, transcript_path = tree_get_selected_paths()
        if transcript_path:
            copy_to_clipboard(os.path.basename(transcript_path))
            set_status("Copied transcript file name to clipboard.")

    def tree_reveal():
        _, transcript_path = tree_get_selected_paths()
        if transcript_path:
            reveal_in_explorer(transcript_path)

    tree_menu.add_command(label="Copy Transcript Full Path", command=tree_copy_full_path)
    tree_menu.add_command(label="Copy Transcript File Name", command=tree_copy_file_name)
    def tree_copy_folder_path():
        _, transcript_path = tree_get_selected_paths()
        if transcript_path:
            copy_to_clipboard(os.path.dirname(transcript_path))
            set_status("Copied transcript folder path to clipboard.")

    def tree_open():
        _, transcript_path = tree_get_selected_paths()
        if transcript_path and os.path.isfile(transcript_path):
            open_with_default_app(transcript_path)

    # --- Move Group (audio/txt/md) support ---
    def _unique_dest_path(dest_dir: str, base_name: str) -> str:
        try:
            candidate = os.path.join(dest_dir, base_name)
            if not os.path.exists(candidate):
                return candidate
            root_name, ext = os.path.splitext(base_name)
            n = 1
            while True:
                alt = os.path.join(dest_dir, f"{root_name} ({n}){ext}")
                if not os.path.exists(alt):
                    return alt
                n += 1
        except Exception:
            return os.path.join(dest_dir, base_name)

    def _get_associated_paths_for_item(item) -> list[tuple[str, str]]:
        # Returns list of (path, friendly_name) for audio, txt, md if present
        out: list[tuple[str, str]] = []
        vals = tree.item(item, "values") or []
        if not vals:
            return out
        audio_display_name = vals[0]
        transcript_val = vals[3] if len(vals) > 3 else None
        folder = current_folder_var.get()
        # transcript
        transcript_path = transcript_val if transcript_val and transcript_val != "(missing)" else None
        if transcript_path and os.path.isfile(transcript_path):
            out.append((transcript_path, os.path.basename(transcript_path)))
        # md derived from transcript
        md_path = md_path_for_transcript(transcript_path) if transcript_path else None
        if md_path and os.path.isfile(md_path):
            out.append((md_path, os.path.basename(md_path)))
        # audio unless this is a standalone row
        if audio_display_name and not audio_display_name.endswith(" (no audio)"):
            try:
                audio_path = os.path.join(folder, display_to_real_filename(audio_display_name))
                if os.path.isfile(audio_path):
                    out.append((audio_path, os.path.basename(audio_path)))
            except Exception:
                pass
        return out

    def on_move_group_selected():
        # Move audio/txt/md associated with the focused row
        item = tree.focus()
        if not item:
            messagebox.showwarning("No selection", "Please select a row to move.")
            return
        folder = current_folder_var.get()
        if not folder:
            return
        paths = _get_associated_paths_for_item(item)
        if not paths:
            messagebox.showinfo("Nothing to move", "No associated files (audio/txt/md) exist on disk.")
            return
        # Ask destination
        dest = filedialog.askdirectory(title="Select destination folder for group move")
        if not dest:
            return
        dest = os.path.abspath(dest)
        if os.path.abspath(dest) == os.path.abspath(folder):
            messagebox.showinfo("Same folder", "Destination is the same as the current folder.")
            return
        errors = []
        moved = []
        for p, name in paths:
            try:
                target = _unique_dest_path(dest, name)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                shutil.move(p, target)
                moved.append((p, target))
            except Exception as e:
                errors.append(f"{name}: {e}")
        # Update UI: remove row from current list
        try:
            tree.delete(item)
        except Exception:
            pass
        # Add destination to recent
        try:
            add_recent_folder(dest)
        except Exception:
            pass
        if errors:
            messagebox.showerror("Move completed with errors", "Some files could not be moved:\n" + "\n".join(errors))
        else:
            messagebox.showinfo("Move complete", f"Moved {len(moved)} file(s) to:\n{dest}")
        set_status("Group move finished.")

    # Add context menu entry for Move Group
    tree_menu.add_separator()
    tree_menu.add_command(label="Move Group (audio/txt/md)...", command=on_move_group_selected)

    def tree_delete_audio_only():
        # Delete only the audio file for the selected row; keep .txt and .md
        item = tree.focus()
        if not item:
            messagebox.showwarning("No selection", "Please select a row.")
            return
        vals = tree.item(item, "values")
        if not vals:
            return
        folder = current_folder_var.get()
        if not folder:
            return
        audio_display_name = vals[0]
        if not audio_display_name or audio_display_name.endswith(" (no audio)") or audio_display_name.endswith(" (md only)"):
            messagebox.showinfo("No audio", "This row has no audio file to delete.")
            return
        audio_path = os.path.join(folder, display_to_real_filename(audio_display_name))
        if not os.path.isfile(audio_path):
            messagebox.showinfo("Missing file", "Audio file does not exist on disk.")
            return
        if not messagebox.askyesno("Delete Audio", f"Move audio to Recycle Bin?\n\n{os.path.basename(audio_path)}", parent=root):
            return
        try:
            safe_delete_to_trash(audio_path)
            # Remove row or update it? Keep row but audio gone; better to remove row and re-populate
            tree.delete(item)
            set_status("Audio deleted.")
        except Exception as e:
            messagebox.showerror("Delete failed", str(e))

    def tree_delete_audio_and_txt_keep_md():
        # Delete audio and associated .txt, keep .md (notes)
        item = tree.focus()
        if not item:
            messagebox.showwarning("No selection", "Please select a row.")
            return
        vals = tree.item(item, "values")
        if not vals:
            return
        folder = current_folder_var.get()
        if not folder:
            return
        audio_display_name = vals[0]
        transcript_val = vals[3] if len(vals) > 3 else None
        candidate_paths = []
        friendly = []
        # audio
        if audio_display_name and not audio_display_name.endswith(" (no audio)") and not audio_display_name.endswith(" (md only)"):
            ap = os.path.join(folder, display_to_real_filename(audio_display_name))
            if os.path.isfile(ap):
                candidate_paths.append(ap)
                friendly.append(os.path.basename(ap))
        # txt
        tp = transcript_val if transcript_val and transcript_val != "(missing)" else None
        if tp and os.path.isfile(tp):
            candidate_paths.append(tp)
            friendly.append(os.path.basename(tp))
        if not candidate_paths:
            messagebox.showinfo("Nothing to delete", "No audio or transcript files found to delete.")
            return
        names = "\n".join(friendly)
        if not messagebox.askyesno("Delete Audio + Transcript", f"Move the following to Recycle Bin (notes .md will be kept):\n\n{names}\n\nProceed?", parent=root):
            return
        errors = []
        for p in candidate_paths:
            try:
                safe_delete_to_trash(p)
            except Exception as e:
                errors.append(f"{os.path.basename(p)}: {e}")
        try:
            tree.delete(item)
        except Exception:
            pass
        if errors:
            messagebox.showerror("Some deletions failed", "\n".join(errors))
        set_status("Audio and transcript deleted; notes kept.")
    def tree_delete_selected_with_associated():
        # Delete the selected row and any associated files: audio, transcript (.txt), and notes (.md)
        item = tree.focus()
        if not item:
            messagebox.showwarning("No selection", "Please select a row to delete.")
            return
        vals = tree.item(item, "values")
        if not vals:
            return
        folder = current_folder_var.get()
        if not folder:
            return
        audio_display_name = vals[0]
        transcript_val = vals[3] if len(vals) > 3 else None

        # Determine actual file paths
        candidate_paths = []
        friendly_list = []

        # Transcript (.txt)
        transcript_path = transcript_val if transcript_val and transcript_val != "(missing)" else None
        if transcript_path and os.path.isfile(transcript_path):
            candidate_paths.append(transcript_path)
            friendly_list.append(os.path.basename(transcript_path))

        # Notes (.md) derived from transcript
        md_path = md_path_for_transcript(transcript_path) if transcript_path else None
        if md_path and os.path.isfile(md_path):
            candidate_paths.append(md_path)
            friendly_list.append(os.path.basename(md_path))

        # Audio file (skip if this is a standalone transcript row shown as "(no audio)")
        if audio_display_name and not audio_display_name.endswith(" (no audio)"):
            audio_path = os.path.join(folder, display_to_real_filename(audio_display_name))
            if os.path.isfile(audio_path):
                candidate_paths.append(audio_path)
                friendly_list.append(os.path.basename(audio_path))

        if not candidate_paths:
            # Nothing to delete on disk; just remove the row after confirmation
            if not messagebox.askyesno("Delete Row", "No associated files found on disk. Remove the row from the list?", parent=root):
                return
            try:
                tree.delete(item)
                set_status("Row removed.")
            except Exception:
                pass
            return

        # Confirm deletion
        names = "\n".join(friendly_list)
        prompt = "move to Recycle Bin" if ensure_send2trash_ready() else "be permanently deleted"
        if not messagebox.askyesno("Delete Files", f"The following files will {prompt}:\n\n{names}\n\nProceed?", parent=root):
            return

        # Attempt deletion (to Recycle Bin when possible)
        errors = []
        for p in candidate_paths:
            try:
                safe_delete_to_trash(p)
            except Exception as e:
                errors.append(f"{os.path.basename(p)}: {e}")

        # Update UI
        try:
            tree.delete(item)
        except Exception:
            pass
        # Clear preview/notes if they were showing the deleted transcript
        try:
            if transcript_path and output_path_var.get().strip() == transcript_path:
                set_preview_text("")
                current_md_path_var.set("")
                notes_editor.delete("1.0", tk.END)
        except Exception:
            pass

        if errors:
            messagebox.showerror("Some deletions failed", "\n".join(errors))
            set_status("Delete completed with errors.")
        else:
            set_status("Selected files deleted and row removed.")

    def tree_rename_pair():
        # Rename audio/video, .txt, and .md associated with the selected row
        item = tree.focus()
        if not item:
            messagebox.showwarning("No selection", "Please select a row in the list.")
            return
        vals = tree.item(item, "values")
        if not vals:
            return
        folder = current_folder_var.get()
        if not folder:
            return

        audio_display_name = vals[0]
        transcript_val = vals[3] if len(vals) > 3 else None

        # Resolve existing associated paths
        audio_path = None
        if audio_display_name and not audio_display_name.endswith(" (no audio)") and not audio_display_name.endswith(" (md only)"):
            try:
                audio_path = os.path.join(folder, display_to_real_filename(audio_display_name))
                if not os.path.isfile(audio_path):
                    audio_path = None
            except Exception:
                audio_path = None

        transcript_path = transcript_val if transcript_val and transcript_val != "(missing)" and os.path.isfile(transcript_val) else None
        md_path = md_path_for_transcript(transcript_path) if transcript_path else None
        if md_path and not os.path.isfile(md_path):
            md_path = None
        # If there is no transcript-derived MD, try deriving MD directly from the display name (handles 'md only' rows)
        if md_path is None:
            try:
                disp = display_to_real_filename(audio_display_name)
                # Strip UI suffixes
                base_guess = disp.replace(" (md only)", "").replace(" (no audio)", "")
                base_guess = os.path.splitext(base_guess)[0]
                candidate_md = os.path.join(folder, base_guess + ".md")
                if os.path.isfile(candidate_md):
                    md_path = candidate_md
            except Exception:
                pass

        # Determine current base name to propose
        if transcript_path:
            base_current = os.path.splitext(os.path.basename(transcript_path))[0]
        elif audio_path:
            base_current = os.path.splitext(os.path.basename(audio_path))[0]
        else:
            # Standalone rows: derive from display name (strip UI suffixes and extension)
            name = audio_display_name
            if name.endswith(" (no audio)"):
                name = name[:-11]
            if name.endswith(" (md only)"):
                name = name[:-10]
            base_current = os.path.splitext(name)[0]

        new_base = simpledialog.askstring(
            "Rename",
            "New base name (without extension):",
            initialvalue=base_current,
            parent=root,
        )
        if new_base is None:
            return
        new_base = new_base.strip()
        # Ensure user-supplied name doesn't carry a media or text/markdown extension
        # so that the generated .md never includes video/audio extension like .mp4, .wav, etc.
        try:
            _strip_exts = [
                ".mp3", ".wav", ".m4a", ".flac", ".aac", ".wma", ".ogg", ".opus",
                ".mp4", ".mkv", ".mov", ".avi", ".wmv", ".webm", ".m4v",
                ".txt", ".md",
            ]
            # Repeatedly strip any known extension from the end (case-insensitive)
            while True:
                lower = new_base.lower()
                matched = False
                for _ext in _strip_exts:
                    if lower.endswith(_ext):
                        new_base = new_base[: -len(_ext)]
                        matched = True
                        break
                if not matched:
                    break
            new_base = new_base.strip().rstrip('.')  # clean up any trailing dot/space
        except Exception:
            pass
        invalid_chars = ['\\', '/', '\\r', '\\n', ':', '*', '?', '"', '<', '>', '|']
        if not new_base or any(ch in new_base for ch in invalid_chars):
            messagebox.showerror("Invalid name", "Please enter a valid file base name.")
            return
        if new_base == base_current:
            return  # nothing to do

        # Compute target paths preserving audio extension
        new_audio_path = None
        new_audio_display_name = None
        if audio_path:
            ext = os.path.splitext(audio_path)[1]
            new_audio_display_name = new_base + ext
            new_audio_path = os.path.join(folder, new_audio_display_name)
        elif audio_display_name.endswith(" (no audio)"):
            new_audio_display_name = f"{new_base} (no audio)"
        elif audio_display_name.endswith(" (md only)"):
            new_audio_display_name = f"{new_base} (md only)"

        new_txt_path = os.path.join(folder, new_base + ".txt") if transcript_path else None
        new_md_path = os.path.join(folder, new_base + ".md") if (md_path or transcript_path) else None

        # Check conflicts
        conflicts = []
        if new_audio_path and os.path.exists(new_audio_path):
            conflicts.append(os.path.basename(new_audio_path))
        if new_txt_path and os.path.exists(new_txt_path):
            conflicts.append(os.path.basename(new_txt_path))
        if new_md_path and os.path.exists(new_md_path):
            conflicts.append(os.path.basename(new_md_path))
        if conflicts:
            names = "\n".join(conflicts)
            if not messagebox.askyesno("Overwrite?", f"The following files already exist and will be overwritten:\n\n{names}\n\nProceed?", parent=root):
                return

        # Execute renames
        try:
            if audio_path and new_audio_path and audio_path != new_audio_path:
                os.replace(audio_path, new_audio_path)
            if transcript_path and new_txt_path and transcript_path != new_txt_path:
                try:
                    os.replace(transcript_path, new_txt_path)
                    transcript_path = new_txt_path
                except Exception as e:
                    messagebox.showwarning("Partial rename", f"Audio renamed but transcript could not be renamed.\n\n{e}")
            if (md_path or (transcript_path and new_md_path)):
                # If md exists, rename it; if not, leave it missing
                if md_path and new_md_path and md_path != new_md_path and os.path.isfile(md_path):
                    try:
                        os.replace(md_path, new_md_path)
                        md_path = new_md_path
                    except Exception as e:
                        messagebox.showwarning("Partial rename", f"Markdown could not be renamed.\n\n{e}")

            # Update UI row
            try:
                if audio_path:
                    # Decide emoji for video types
                    disp_name = new_audio_display_name
                    try:
                        if is_video_file(new_audio_path):
                            disp_name = "🎥 " + new_audio_display_name
                    except Exception:
                        pass
                    tree.set(item, "audio", disp_name)
                else:
                    # Standalone rows retain suffix
                    if new_audio_display_name:
                        tree.set(item, "audio", new_audio_display_name)

                if transcript_path:
                    tree.set(item, "transcript", new_txt_path or transcript_path)
                else:
                    tree.set(item, "transcript", "(missing)")
            except Exception:
                pass

            # Update mapping for path_to_item (audio)
            try:
                if audio_path and new_audio_path and audio_path in path_to_item:
                    iid_ref = path_to_item.pop(audio_path)
                    path_to_item[new_audio_path] = iid_ref
            except Exception:
                pass

            # Update Notes tab to new md (if any) and refresh preview
            try:
                if new_md_path and os.path.isfile(new_md_path):
                    current_md_path_var.set(new_md_path)
                else:
                    current_md_path_var.set("")
            except Exception:
                pass
            try:
                notes_editor.delete("1.0", tk.END)
                if new_md_path and os.path.isfile(new_md_path):
                    with open(new_md_path, "r", encoding="utf-8", errors="replace") as f:
                        notes_editor.insert(tk.END, f.read())
                content = notes_editor.get("1.0", tk.END)
                render_markdown_to_preview(content)
            except Exception:
                pass

            set_status("Renamed associated files.")
        except Exception as e:
            messagebox.showerror("Rename failed", f"Could not rename files.\n\n{e}")

    tree_menu.add_separator()
    tree_menu.add_command(label="Delete Audio Only", command=tree_delete_audio_only)
    tree_menu.add_command(label="Delete Audio + Transcript (keep .md)", command=tree_delete_audio_and_txt_keep_md)
    tree_menu.add_command(label="Delete Selected (audio/txt/md)…", command=tree_delete_selected_with_associated)
    tree_menu.add_command(label="Rename Associated Files (audio/txt/md)…", command=tree_rename_pair)
    tree_menu.add_command(label="Copy Transcript Folder Path", command=tree_copy_folder_path)
    tree_menu.add_command(label="Open Transcript", command=tree_open)
    tree_menu.add_command(label="Reveal Transcript in Explorer", command=tree_reveal)

    def on_tree_right_click(event):
        # Select the item under cursor first
        iid = tree.identify_row(event.y)
        if iid:
            tree.selection_set(iid)
            tree.focus(iid)
        try:
            tree_menu.tk_popup(event.x_root, event.y_root)
        finally:
            tree_menu.grab_release()

    select_btn.configure(command=on_select_audio)
    browse_btn.configure(command=on_browse_folder)
    transcribe_url_btn.configure(command=on_transcribe_url)
    transcribe_sel_btn.configure(command=on_transcribe_selected)
    auto_fit_btn.configure(command=on_autofit_columns)
    add_md_btn.configure(command=on_add_md_only)
    recent_open_btn.configure(command=open_recent_selected)
    notes_save_btn.configure(command=on_save_notes)
    notes_reveal_btn.configure(command=on_reveal_notes)
    move_group_btn.configure(command=on_move_group_selected)
    tree.bind("<Double-1>", on_tree_double_click)
    tree.bind("<Button-3>", on_tree_right_click)
    # Single selection handler: prefer Markdown > TXT > Log
    tree.bind("<<TreeviewSelect>>", on_tree_select)
    recent_combo.bind("<<ComboboxSelected>>", lambda e: open_recent_selected())

    # Debounced live preview and auto-save while typing
    _md_preview_job = None
    _md_autosave_job = None
    def _on_notes_keypress(event=None):
        nonlocal _md_preview_job, _md_autosave_job
        # Debounce preview update
        try:
            if _md_preview_job is not None:
                root.after_cancel(_md_preview_job)
        except Exception:
            pass
        def do_update_preview():
            try:
                content = notes_editor.get("1.0", tk.END)
            except Exception:
                content = ""
            render_markdown_to_preview(content)
        _md_preview_job = root.after(300, do_update_preview)

        # Debounce auto-save to disk (respect toggle and delay)
        try:
            if _md_autosave_job is not None:
                root.after_cancel(_md_autosave_job)
        except Exception:
            pass
        def do_autosave():
            md_path = current_md_path_var.get().strip()
            if not md_path:
                return
            try:
                os.makedirs(os.path.dirname(md_path), exist_ok=True)
                content = notes_editor.get("1.0", tk.END)
                with open(md_path, "w", encoding="utf-8") as f:
                    f.write(content)
                # Light-touch status update without interrupting flow
                try:
                    set_status(f"Auto-saved notes: {os.path.basename(md_path)}")
                    saved_at_var.set(f"Saved at {datetime.now().strftime('%H:%M:%S')}")
                except Exception:
                    pass
            except Exception:
                # Silent fail for autosave to avoid modal interruptions while typing
                pass
        # Only schedule autosave if enabled
        try:
            if autosave_enabled_var.get():
                delay_ms = int(max(0.0, float(autosave_delay_s_var.get())) * 1000)
                if delay_ms < 50:
                    delay_ms = 50
                _md_autosave_job = root.after(delay_ms, do_autosave)
        except Exception:
            # Fallback to default 1000 ms if something goes wrong reading the delay
            _md_autosave_job = root.after(1000, do_autosave)
    notes_editor.bind("<KeyRelease>", _on_notes_keypress)

    # Auto-fit on window resize with debounce
    resize_job_id = None

    def on_root_resize(event):
        nonlocal resize_job_id
        # Only respond to root window resize events
        if event.widget is not root:
            return
        if resize_job_id is not None:
            try:
                root.after_cancel(resize_job_id)
            except Exception:
                pass
        # Debounce: run after 150 ms
        def do_fit():
            try:
                autofit_tree_columns(tree, cols, min_widths={"size": 80, "modified": 140}, padding=18)
            except Exception:
                pass
        resize_job_id = root.after(150, do_fit)

    root.bind("<Configure>", on_root_resize)

    # Ready
    set_status("Model loaded. Ready to transcribe.")
    # Bind selection event handler already set above
    # Load recent folders on startup
    try:
        set_recent_values(load_recent_folders())
    except Exception:
        pass
    # Auto-open last folder if available
    try:
        last = load_last_folder()
        if last:
            current_folder_var.set(last)
            populate_tree(last)
            # Reflect in Recent dropdown and selection
            add_recent_folder(last)
            recent_var.set(last)
            open_recent_selected()
    except Exception:
        pass
    root.mainloop()


if __name__ == "__main__":
    main()

# choco install ffmpeg
# ffmpeg -version
# pip install torch
# python -c "import torch; print(torch.cuda.is_available())"
# pip install -U openai-whisper
# whisper --help
# python "C:\\Users\\JueShi\\OneDrive - Astera Labs, Inc\\Documents\\windsurf\\audio2text.py"

# working
# & 'c:\Program Files\Python311\python.exe' 'c:\Users\juesh\.windsurf\extensions\ms-python.debugpy-2025.10.0-win32-x64\bundled\libs\debugpy\launcher' '64312' '--' 'c:\Users\juesh\OneDrive\Documents\windsurf\stock_charts_10k10q\audio2ext_v1.1_path.py' 

# not working
# & 'c:\Users\juesh\AppData\Local\Programs\Python\Python313\python.exe' 'c:\Users\juesh\.windsurf\extensions\ms-python.debugpy-2025.10.0-win32-x64\bundled\libs\debugpy\launcher' '53222' '--' 'c:\Users\juesh\OneDrive\Documents\pandastable\examples\audio2ext_v1.1_path.py' 
      