"""Tests for UI layer view-model state management."""

from __future__ import annotations

from pathlib import Path

from gol_multiworld.sim.layers import LayerId
from gol_multiworld.ui.layer_manager import LayerManager


def test_toggle_visibility_updates_renderable_layers(tmp_path: Path) -> None:
    manager = LayerManager(
        storage_key="test_toggle_visibility",
        storage_scope="session",
        storage_dir=tmp_path,
    )
    manager.toggle_visibility(LayerId.RESOURCES)

    assert LayerId.RESOURCES not in manager.get_renderable_layers()


def test_set_opacity_clamps_to_valid_range(tmp_path: Path) -> None:
    manager = LayerManager(
        storage_key="test_opacity",
        storage_scope="session",
        storage_dir=tmp_path,
    )

    assert manager.set_opacity(LayerId.BASE_TILES, 2.5) == 1.0
    assert manager.set_opacity(LayerId.BASE_TILES, -1.0) == 0.0


def test_solo_layers_override_visibility_filter(tmp_path: Path) -> None:
    manager = LayerManager(
        storage_key="test_solo",
        storage_scope="session",
        storage_dir=tmp_path,
    )
    manager.set_solo(LayerId.ORGANISMS, True)
    manager.toggle_visibility(LayerId.ORGANISMS)

    assert manager.get_renderable_layers() == [LayerId.ORGANISMS]


def test_persists_and_loads_saved_view_state(tmp_path: Path) -> None:
    storage_key = "test_persist_layer_view_state"
    manager = LayerManager(
        storage_key=storage_key,
        storage_scope="session",
        storage_dir=tmp_path,
    )
    manager.set_opacity(LayerId.RESOURCES, 0.42)
    manager.set_locked(LayerId.RESOURCES, True)

    reloaded = LayerManager(
        storage_key=storage_key,
        storage_scope="session",
        storage_dir=tmp_path,
    )
    vm = reloaded.layers[LayerId.RESOURCES]
    assert vm.opacity == 0.42
    assert vm.locked is True
