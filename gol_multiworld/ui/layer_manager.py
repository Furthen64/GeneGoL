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
ViewPreset = Literal["Ecology", "Genetics", "Structure"]


@dataclass
class LayerViewModel:
    """Render/edit state for a single simulation layer in the UI."""

    visible: bool = True
    opacity: float = 1.0
    blendMode: BlendMode = "normal"
    solo: bool = False
    locked: bool = False


_LAYER_LABELS: dict[LayerId, str] = {
    LayerId.BASE_TILES: "Base",
    LayerId.RESOURCES: "Environment",
    LayerId.ORGANISMS: "Organisms",
    LayerId.GENES: "Genes",
}

_LAYER_GROUPS: dict[str, list[LayerId]] = {
    "Group A: Simulation substrate": [LayerId.BASE_TILES],
    "Group B: Environment": [LayerId.RESOURCES],
    "Group C: Biology/Genes": [LayerId.ORGANISMS, LayerId.GENES],
}

_PRESET_VISIBILITY: dict[ViewPreset, dict[LayerId, bool]] = {
    "Ecology": {
        LayerId.BASE_TILES: False,
        LayerId.RESOURCES: True,
        LayerId.ORGANISMS: True,
        LayerId.GENES: False,
    },
    "Genetics": {
        LayerId.BASE_TILES: False,
        LayerId.RESOURCES: False,
        LayerId.ORGANISMS: True,
        LayerId.GENES: True,
    },
    "Structure": {
        LayerId.BASE_TILES: True,
        LayerId.RESOURCES: True,
        LayerId.ORGANISMS: False,
        LayerId.GENES: False,
    },
}


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

    def set_visibility(self, layer_id: LayerId, visible: bool) -> bool:
        """Set and persist visibility for a layer."""
        self.layers[layer_id].visible = visible
        self._save()
        return visible

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

    def toggle_solo(self, layer_id: LayerId) -> bool:
        """Toggle and persist solo state for a layer."""
        vm = self.layers[layer_id]
        vm.solo = not vm.solo
        self._save()
        return vm.solo

    def set_locked(self, layer_id: LayerId, locked: bool) -> bool:
        """Set and persist editing lock for a layer."""
        self.layers[layer_id].locked = locked
        self._save()
        return locked

    def toggle_locked(self, layer_id: LayerId) -> bool:
        """Toggle and persist editing lock state for a layer."""
        vm = self.layers[layer_id]
        vm.locked = not vm.locked
        self._save()
        return vm.locked

    def apply_preset(self, preset_name: ViewPreset) -> None:
        """Apply a named visibility preset and clear solo mode."""
        for layer_id, visible in _PRESET_VISIBILITY[preset_name].items():
            vm = self.layers[layer_id]
            vm.visible = visible
            vm.solo = False
        self._save()

    def toggle_group_visibility(self, group_name: str) -> bool:
        """Toggle all layer visibilities in a group. Returns new common visibility."""
        group = _LAYER_GROUPS[group_name]
        target_visible = not all(self.layers[layer_id].visible for layer_id in group)
        for layer_id in group:
            self.layers[layer_id].visible = target_visible
        self._save()
        return target_visible

    def layer_label(self, layer_id: LayerId) -> str:
        """Human-readable label for UI rows."""
        return _LAYER_LABELS[layer_id]

    def groups(self) -> dict[str, list[LayerId]]:
        """Layer grouping metadata for UI organization."""
        return {name: list(ids) for name, ids in _LAYER_GROUPS.items()}

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
