from __future__ import annotations

from pathlib import Path
import shutil
import os
import platform
import subprocess
from typing import Callable, Dict, List, Sequence, Tuple

import pandas as pd

Record = Dict[str, str]


def build_template_context(record: Record) -> Dict[str, str]:
    """Return formatting context for rename templates."""
    path = Path(record['Path'])
    context: Dict[str, str] = {
        'name': path.name,
        'stem': path.stem,
        'suffix': path.suffix,
        'ext': path.suffix,
        'extension': path.suffix,
        'directory': str(path.parent),
    }
    for key, value in record.items():
        if key.startswith('Part '):
            context[key.replace(' ', '_')] = value
    return context


def apply_rename_template(record: Record, template: str) -> str:
    context = build_template_context(record)
    try:
        candidate = template.format(**context)
    except KeyError as exc:
        raise ValueError(f"Unknown placeholder: {exc.args[0]}") from exc
    if not candidate:
        raise ValueError("Template cannot produce an empty name")
    if not Path(candidate).suffix:
        candidate = f"{candidate}{Path(record['Path']).suffix}"
    return candidate


def copy_or_move_files(
    records: Sequence[Record],
    destination: str,
    overwrite: bool,
    operation: str,
) -> Tuple[str, str, List[str], List[str]]:
    if operation not in {'copy', 'move'}:
        raise ValueError("operation must be 'copy' or 'move'")
    if not records:
        return "warning", "Select one or more files in the sidebar.", [], []
    if not destination:
        return "error", "Enter a destination directory.", [], []

    dest_path = Path(destination).expanduser()
    try:
        dest_path.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        return "error", f"Unable to access destination: {exc}", [], []

    successes: List[str] = []
    failures: List[str] = []
    mutated_sources: List[str] = []
    for record in records:
        src = Path(record['Path'])
        if not src.exists():
            failures.append(f"{src.name}: missing source")
            continue
        target = dest_path / src.name
        if target.exists():
            if overwrite:
                try:
                    if target.is_file():
                        target.unlink()
                    else:
                        shutil.rmtree(target)
                except Exception as exc:
                    failures.append(f"{src.name}: unable to overwrite ({exc})")
                    continue
            else:
                failures.append(f"{src.name}: destination exists")
                continue
        try:
            if operation == 'copy':
                shutil.copy2(src, target)
            else:
                shutil.move(str(src), str(target))
                mutated_sources.append(str(src))
        except Exception as exc:
            failures.append(f"{src.name}: {exc}")
        else:
            successes.append(target.name)

    summary = (
        f"{operation.title()}d {len(successes)} file(s) to {dest_path}"
        if successes
        else "No files processed."
    )
    if failures and successes:
        failure_msg = "; ".join(failures[:3])
        return "warning", f"{summary} Issues: {failure_msg}", successes, mutated_sources
    if failures and not successes:
        failure_msg = "; ".join(failures[:3])
        return "error", f"Operation failed: {failure_msg}", [], mutated_sources
    return "success", summary, successes, mutated_sources


def rename_files(
    records: Sequence[Record],
    template: str,
    overwrite: bool,
) -> Tuple[str, str, List[str], List[str]]:
    if not records:
        return "warning", "Select one or more files in the sidebar.", [], []
    if not template.strip():
        return "error", "Enter a rename template (e.g., {Part_1}_{stem}).", [], []

    successes: List[str] = []
    failures: List[str] = []
    mutated_sources: List[str] = []
    for record in records:
        src = Path(record['Path'])
        if not src.exists():
            failures.append(f"{src.name}: missing source")
            continue
        try:
            target_name = apply_rename_template(record, template)
        except ValueError as exc:
            return "error", str(exc), [], []
        target = src.with_name(target_name)
        if target.exists():
            if overwrite:
                try:
                    target.unlink()
                except Exception as exc:
                    failures.append(f"{src.name}: unable to overwrite ({exc})")
                    continue
            else:
                failures.append(f"{src.name}: destination exists")
                continue
        try:
            src.rename(target)
        except Exception as exc:
            failures.append(f"{src.name}: {exc}")
        else:
            successes.append(f"{src.name} → {target.name}")
            mutated_sources.append(str(src))

    if successes and not failures:
        return "success", f"Renamed {len(successes)} file(s).", successes, mutated_sources
    if successes and failures:
        failure_msg = "; ".join(failures[:3])
        return "warning", f"Renamed {len(successes)} file(s) with issues: {failure_msg}", successes, mutated_sources
    failure_msg = "; ".join(failures[:3]) if failures else "No files matched criteria."
    return "error", failure_msg, successes, mutated_sources


def delete_files(records: Sequence[Record]) -> Tuple[str, str, List[str], List[str]]:
    if not records:
        return "warning", "Select one or more files in the sidebar.", [], []

    successes: List[str] = []
    failures: List[str] = []
    mutated_sources: List[str] = []
    for record in records:
        src = Path(record['Path'])
        if not src.exists():
            failures.append(f"{src.name}: missing source")
            continue
        try:
            src.unlink()
        except Exception as exc:
            failures.append(f"{src.name}: {exc}")
        else:
            successes.append(src.name)
            mutated_sources.append(str(src))

    if successes and not failures:
        return "success", f"Deleted {len(successes)} file(s).", successes, mutated_sources
    if successes and failures:
        failure_msg = "; ".join(failures[:3])
        return "warning", f"Deleted {len(successes)} file(s) with issues: {failure_msg}", successes, mutated_sources
    failure_msg = "; ".join(failures[:3]) if failures else "Nothing deleted."
    return "error", failure_msg, successes, mutated_sources


def preview_rename(records: Sequence[Record], template: str, limit: int = 3) -> List[Dict[str, str]]:
    previews: List[Dict[str, str]] = []
    if not template.strip():
        return previews
    for record in records[:limit]:
        try:
            new_name = apply_rename_template(record, template)
        except Exception:
            new_name = "<invalid template>"
        previews.append({
            'original': Path(record['Path']).name,
            'preview': Path(new_name).name,
        })
    return previews


def merge_csv_files(
    records: Sequence[Record],
    output_path: str,
    include_header: bool = True,
) -> Tuple[str, str, List[str], List[str]]:
    if not records:
        return "warning", "Select one or more files in the sidebar.", [], []
    if not output_path or not output_path.strip():
        return "error", "Enter a destination file path for the merged CSV.", [], []

    dest = Path(output_path).expanduser()
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        return "error", f"Unable to create destination directory: {exc}", [], []

    frames: List[pd.DataFrame] = []
    failures: List[str] = []
    for record in records:
        path = Path(record['Path'])
        if not path.exists():
            failures.append(f"{path.name}: missing source")
            continue
        try:
            df = pd.read_csv(path)
        except Exception as exc:
            failures.append(f"{path.name}: {exc}")
            continue
        frames.append(df)

    if not frames:
        failure_msg = "; ".join(failures[:3]) if failures else "No CSV data to merge."
        return "error", failure_msg, [], []

    merged = pd.concat(frames, ignore_index=True, sort=False)
    try:
        merged.to_csv(dest, index=False, header=include_header)
    except Exception as exc:
        return "error", f"Failed to write merge output: {exc}", [], []

    summary = f"Merged {len(frames)} file(s) into {dest} ({len(merged)} rows)."
    if failures:
        return "warning", summary + " Issues: " + "; ".join(failures[:3]), [str(dest)], []
    return "success", summary, [str(dest)], []


def open_in_app(
    records: Sequence[Record],
    mode: str = 'default',
    launcher: Callable[[Path, str], None] | None = None,
) -> Tuple[str, str, List[str], List[str]]:
    if not records:
        return "warning", "Select one or more files in the sidebar.", [], []
    if launcher is None:
        launcher = _default_launcher

    successes: List[str] = []
    failures: List[str] = []
    for record in records:
        path = Path(record['Path'])
        if not path.exists():
            failures.append(f"{path.name}: missing source")
            continue
        try:
            launcher(path, mode)
        except Exception as exc:
            failures.append(f"{path.name}: {exc}")
        else:
            successes.append(path.name)

    if successes and not failures:
        return "success", f"Opened {len(successes)} file(s) via system handler.", successes, []
    if successes and failures:
        return "warning", f"Opened {len(successes)} file(s) with issues: " + "; ".join(failures[:3]), successes, []
    failure_msg = "; ".join(failures[:3]) if failures else "No files opened."
    return "error", failure_msg, successes, []


def _default_launcher(path: Path, mode: str) -> None:
    system = platform.system().lower()
    if system == 'windows':
        os.startfile(str(path))  # type: ignore[attr-defined]
        return

    if system == 'darwin':
        if mode == 'excel':
            cmd = ['open', '-a', 'Microsoft Excel', str(path)]
        elif mode == 'spotfire':
            cmd = ['open', '-a', 'Spotfire', str(path)]
        else:
            cmd = ['open', str(path)]
    else:
        cmd = ['xdg-open', str(path)]
    subprocess.Popen(cmd)
