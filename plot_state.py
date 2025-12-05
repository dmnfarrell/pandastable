import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

DEFAULT_PLOT_STATE: Dict[str, Any] = {
    "general": {
        "plot_type": "Scatter",
        "scatter": {"x": None, "y": None, "color": None},
        "line": {"x": None, "ys": []},
        "histogram": {"column": None, "bins": 20},
        "bar": {"category": None, "value": None, "agg": "Sum"},
        "barh": {"category": None, "value": None, "agg": "Sum"},
        "pie": {"category": None, "value": None, "agg": "Sum"},
        "box": {"columns": []},
        "violin": {"columns": []},
        "density": {"columns": [], "bw_method": "scott", "fill": False, "show_rug": False},
        "area": {"columns": [], "stacked": True},
        "dot": {"category": None, "value": None},
        "heatmap": {"columns": []},
        "hexbin": {"x": None, "y": None, "gridsize": 30},
        "contour": {"x": None, "y": None, "z": None, "levels": 10},
        "imshow": {"columns": []},
        "scatter_matrix": {"columns": []},
        "radviz": {"columns": [], "class_column": None},
        "venn": {"sets": []},
        "gantt": {
            "task": None,
            "start": None,
            "end": None,
            "group": None,
            "progress": None,
        }
    },
    "correlation": {"target": None, "top_n": 5},
    "special": {
        "plot_type": "Shmoo",
        "shmoo": {"x": None, "y": None, "z": None, "threshold_min": "", "threshold_max": ""},
        "bathtub": {"x": None, "ys": [], "target": "1e-12"},
        "eye": {"time": None, "voltage": None, "ui": 1.0},
        "three_d": {
            "mode": "Scatter",
            "x": None,
            "y": None,
            "z": None,
            "colormap": "viridis",
            "log_z": False,
            "stride": 2,
            "show_points": False,
            "resolution": 50,
        },
        "jitter": {
            "column": None,
            "bins": 50,
            "show_gaussian": True,
            "show_stats": True,
        },
        "phase_noise": {
            "freq_col": None,
            "noise_col": None,
            "carrier_hz": 1e9,
        },
    },
}


class PlotStateManager:
    """Lightweight persistence layer for plot configurations keyed by file path."""

    def __init__(self, storage_path: str | None = None) -> None:
        default_dir = Path.home() / ".csv_browser_web"
        self.storage_path = Path(storage_path) if storage_path else default_dir / "plot_settings.json"
        self._data: Dict[str, Any] = {}
        self._load()

    def _normalize_key(self, file_key: str | None) -> str:
        if not file_key:
            return ""
        try:
            return str(Path(file_key).expanduser().resolve())
        except Exception:
            return str(file_key)

    def _load(self) -> None:
        try:
            if self.storage_path.exists():
                with self.storage_path.open("r", encoding="utf-8") as f:
                    self._data = json.load(f)
            else:
                self._data = {}
        except Exception:
            # Fallback to in-memory defaults on any error
            self._data = {}

    def _save(self) -> None:
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with self.storage_path.open("w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
        except Exception:
            # Ignore persistence errors so UI remains usable
            pass

    def _default_state(self) -> Dict[str, Any]:
        return deepcopy(DEFAULT_PLOT_STATE)

    def get(self, file_key: str) -> Dict[str, Any]:
        key = self._normalize_key(file_key)
        stored = self._data.get(key)
        if not stored:
            return self._default_state()
        return self._merge_with_defaults(stored)

    def update(self, file_key: str, payload: Dict[str, Any]) -> None:
        key = self._normalize_key(file_key)
        self._data[key] = payload
        self._save()

    def reset(self, file_key: str) -> Dict[str, Any]:
        key = self._normalize_key(file_key)
        if key in self._data:
            del self._data[key]
            self._save()
        return self._default_state()

    def export_state(self, file_key: str) -> Dict[str, Any]:
        return deepcopy(self.get(file_key))

    def export_to_file(self, file_key: str, destination: str | Path) -> Path:
        payload = self.export_state(file_key)
        destination_path = Path(destination)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        with destination_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return destination_path

    def import_state(self, file_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("Plot settings payload must be a dict")
        merged = self._merge_with_defaults(payload)
        self.update(file_key, merged)
        return merged

    def import_from_file(self, file_key: str, source_path: str | Path) -> Dict[str, Any]:
        source = Path(source_path)
        with source.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        return self.import_state(file_key, payload)

    def _merge_with_defaults(self, stored: Dict[str, Any]) -> Dict[str, Any]:
        merged = self._default_state()
        for section, values in stored.items():
            if section in merged and isinstance(values, dict):
                merged_section = merged[section]
                for key, value in values.items():
                    if isinstance(value, dict) and key in merged_section:
                        merged_section[key].update(value)
                    else:
                        merged_section[key] = value
            else:
                merged[section] = values
        return merged


def sanitize_session_key(*parts: str) -> str:
    """Create a Streamlit-friendly session key using safe characters."""
    safe = ["".join(ch for ch in part if ch.isalnum() or ch in ("_", "-")) for part in parts]
    return "__".join(filter(None, safe))
