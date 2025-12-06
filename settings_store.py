import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List

DEFAULT_SETTINGS: Dict[str, Any] = {
    "recent_directories": [],
    "saved_filters": {
        "file": [],
        "row": [],
        "column": [],
        "file_op_dest": [],
        "file_op_template": [],
        "column_display": [],
    }
}


class SettingsManager:
    """Persistent storage for frequently used directories and filter presets."""

    def __init__(self, storage_path: str | None = None, max_recent: int = 10) -> None:
        default_dir = Path.home() / ".csv_browser_web"
        self.storage_path = Path(storage_path) if storage_path else default_dir / "settings.json"
        self.max_recent = max_recent
        self._data: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        try:
            if self.storage_path.exists():
                with self.storage_path.open("r", encoding="utf-8") as f:
                    self._data = json.load(f)
            else:
                self._data = deepcopy(DEFAULT_SETTINGS)
        except Exception:
            self._data = deepcopy(DEFAULT_SETTINGS)

    def _save(self) -> None:
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with self.storage_path.open("w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
        except Exception:
            pass

    def _ensure_defaults(self) -> None:
        if not self._data:
            self._data = deepcopy(DEFAULT_SETTINGS)
        if "recent_directories" not in self._data:
            self._data["recent_directories"] = []
        if "saved_filters" not in self._data:
            self._data["saved_filters"] = deepcopy(DEFAULT_SETTINGS["saved_filters"])
        else:
            for key in DEFAULT_SETTINGS["saved_filters"].keys():
                self._data["saved_filters"].setdefault(key, [])

    def get_recent_directories(self) -> List[str]:
        self._ensure_defaults()
        return list(self._data.get("recent_directories", []))

    def add_recent_directory(self, directory: str) -> None:
        self._ensure_defaults()
        if not directory:
            return
        norm_dir = str(Path(directory))
        recent = self._data.setdefault("recent_directories", [])
        if norm_dir in recent:
            recent.remove(norm_dir)
        recent.insert(0, norm_dir)
        del recent[self.max_recent:]
        self._save()

    def get_saved_filters(self, category: str) -> List[str]:
        self._ensure_defaults()
        return list(self._data.get("saved_filters", {}).get(category, []))

    def add_saved_filter(self, category: str, value: str, max_entries: int = 20) -> None:
        self._ensure_defaults()
        if not value:
            return
        filters = self._data.setdefault("saved_filters", {}).setdefault(category, [])
        if value in filters:
            filters.remove(value)
        filters.insert(0, value)
        del filters[max_entries:]
        self._save()

    def remove_saved_filter(self, category: str, value: str) -> None:
        self._ensure_defaults()
        filters = self._data.setdefault("saved_filters", {}).setdefault(category, [])
        if value in filters:
            filters.remove(value)
            self._save()

    def export(self) -> Dict[str, Any]:
        self._ensure_defaults()
        return deepcopy(self._data)

    def import_settings(self, payload: Dict[str, Any]) -> None:
        if not isinstance(payload, dict):
            raise ValueError("Settings payload must be a dict")
        merged = deepcopy(DEFAULT_SETTINGS)
        merged.update({k: v for k, v in payload.items() if k in DEFAULT_SETTINGS})
        self._data = merged
        self._save()
