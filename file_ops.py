from __future__ import annotations

from pathlib import Path
import shutil
from typing import Dict, List, Sequence, Tuple

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
