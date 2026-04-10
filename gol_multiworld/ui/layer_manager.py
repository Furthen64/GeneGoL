"""UI-facing view-model and manager for render-layer settings."""

from __future__ import annotations

import json
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from gol_multiworld.sim.layers import LayerId

BlendMode = Literal["normal", "multiply", "add"]
StorageScope = Literal["session", "local"]


@dataclass
class LayerViewModel:
    """Render/edit state for a single simulation layer in the UI."""

    visible: bool = True
    opacity: float = 1.0
    blendMode: BlendMode = "normal"
    solo: bool = False
    locked: bool = False


class LayerManager:
    """Manage layer view state separately from simulation layer data."""

    def __init__(
        self,
        storage_key: str = "genegol.layer_view_state.v1",
        storage_scope: StorageScope = "local",
        storage_dir: Path | None = None,
    ) -> None:
        self.storage_key = storage_key
        self.storage_scope = storage_scope
        self.storage_dir = storage_dir
        self.layers: dict[LayerId, LayerViewModel] = {
            layer_id: LayerViewModel() for layer_id in LayerId
        }
        self._load()

    def toggle_visibility(self, layer_id: LayerId) -> bool:
        """Toggle and persist visibility for a layer."""
        vm = self.layers[layer_id]
        vm.visible = not vm.visible
        self._save()
        return vm.visible

    def set_opacity(self, layer_id: LayerId, opacity: float) -> float:
        """Set and persist opacity for a layer in [0, 1]."""
        clamped = max(0.0, min(1.0, float(opacity)))
        self.layers[layer_id].opacity = clamped
        self._save()
        return clamped

    def set_solo(self, layer_id: LayerId, solo: bool) -> bool:
        """Set and persist solo state for a layer."""
        self.layers[layer_id].solo = solo
        self._save()
        return solo

    def set_locked(self, layer_id: LayerId, locked: bool) -> bool:
        """Set and persist editing lock for a layer."""
        self.layers[layer_id].locked = locked
        self._save()
        return locked

    def get_renderable_layers(self) -> list[LayerId]:
        """Return layer ids that should be rendered in draw order."""
        solo_layers = [layer_id for layer_id, vm in self.layers.items() if vm.solo]
        if solo_layers:
            return solo_layers
        return [layer_id for layer_id, vm in self.layers.items() if vm.visible]

    def _storage_path(self) -> Path:
        if self.storage_dir is not None:
            return self.storage_dir / f"{self.storage_key}.json"
        if self.storage_scope == "session":
            return Path(tempfile.gettempdir()) / f"{self.storage_key}.json"
        return Path.home() / ".genegol" / f"{self.storage_key}.json"

    def _load(self) -> None:
        path = self._storage_path()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return

        layers_payload = payload.get("layers", {})
        for layer_id in LayerId:
            raw = layers_payload.get(str(int(layer_id)))
            if not isinstance(raw, dict):
                continue
            vm = self.layers[layer_id]
            vm.visible = bool(raw.get("visible", vm.visible))
            vm.opacity = max(0.0, min(1.0, float(raw.get("opacity", vm.opacity))))
            blend_mode = raw.get("blendMode", vm.blendMode)
            vm.blendMode = blend_mode if blend_mode in {"normal", "multiply", "add"} else "normal"
            vm.solo = bool(raw.get("solo", vm.solo))
            vm.locked = bool(raw.get("locked", vm.locked))

    def _save(self) -> None:
        path = self._storage_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "layers": {
                str(int(layer_id)): asdict(vm)
                for layer_id, vm in self.layers.items()
            }
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def getRenderableLayers(layer_manager: LayerManager) -> list[LayerId]:
    """Compatibility helper for renderer codepaths expecting camelCase name."""
    return layer_manager.get_renderable_layers()
