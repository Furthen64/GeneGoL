"""Simulation birth-cause tracing and invariant checks."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
import sys
from typing import TYPE_CHECKING, TextIO

from gol_multiworld.sim.cell_types import CellType
from gol_multiworld.sim.grid import Grid
from gol_multiworld.sim.visibility import count_visible_live_neighbors

if TYPE_CHECKING:
    from gol_multiworld.sim.organism_detection import Organism


D2_BIRTH = "D2_birth"
D3_FOOD_CONVERSION = "D3_food_conversion"
D3_GUIDED_GROWTH = "D3_guided_growth"
SPAWN = "spawn"
UNKNOWN = "unknown"

_VALID_BIRTH_CAUSES = {
    D2_BIRTH,
    D3_FOOD_CONVERSION,
    D3_GUIDED_GROWTH,
    SPAWN,
    UNKNOWN,
}

_NEIGHBOR_OFFSETS: list[tuple[int, int]] = [
    (-1, -1), (0, -1), (1, -1),
    (-1, 0),           (1, 0),
    (-1, 1),  (0, 1),  (1, 1),
]


@dataclass(frozen=True)
class StateChangeRecord:
    tick: int
    position: tuple[int, int]
    previous_state: int
    new_state: int
    cause: str
    phase: str
    visible_live_neighbor_count: int
    source_organism_id: int | None = None
    near_organism_boundary: bool = False


@dataclass(frozen=True)
class OrganismAppearanceCellRecord:
    position: tuple[int, int]
    source: str
    cause: str | None = None
    origin_tick: int | None = None
    origin_phase: str | None = None


@dataclass(frozen=True)
class OrganismAppearanceRecord:
    organism_id: int
    tick: int
    cells: tuple[OrganismAppearanceCellRecord, ...]


@dataclass
class BirthCauseTracer:
    """Track new live cells and simulation invariants per tick."""

    enabled: bool = False
    strict: bool = False
    stream: TextIO = field(default_factory=lambda: sys.stderr)
    current_tick: int | None = None
    previous_live_cells: set[tuple[int, int]] = field(default_factory=set)
    live_origins: dict[tuple[int, int], StateChangeRecord] = field(default_factory=dict)
    state_changes: dict[tuple[int, int], list[StateChangeRecord]] = field(
        default_factory=lambda: defaultdict(list)
    )
    live_births: dict[tuple[int, int], StateChangeRecord] = field(default_factory=dict)
    d3_write_limits: dict[int, int] = field(default_factory=dict)
    d3_live_writes: dict[int, set[tuple[int, int]]] = field(
        default_factory=lambda: defaultdict(set)
    )
    organism_appearances: list[OrganismAppearanceRecord] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)

    @classmethod
    def from_settings(
        cls,
        rules: dict[str, object],
        *,
        enabled: bool = False,
        strict: bool = False,
    ) -> "BirthCauseTracer":
        return cls(
            enabled=enabled or bool(rules.get("birthCauseDebug", False)),
            strict=strict or bool(rules.get("birthCauseDebugStrict", False)),
        )

    def begin_tick(self, tick: int, grid: Grid) -> None:
        """Reset per-tick state and snapshot the incoming live cells."""
        if not self.enabled:
            return

        self.current_tick = tick
        self.previous_live_cells = _live_cells(grid)
        self.state_changes.clear()
        self.live_births.clear()
        self.d3_write_limits.clear()
        self.d3_live_writes.clear()
        self.organism_appearances.clear()
        self.violations.clear()

    def record_transition(
        self,
        grid: Grid,
        x: int,
        y: int,
        previous_state: int,
        new_state: int,
        *,
        cause: str,
        phase: str,
        source_organism_id: int | None = None,
        near_organism_boundary: bool = False,
        allow_multiple: bool = False,
    ) -> None:
        """Record a cell state change and validate live births."""
        if not self.enabled or previous_state == new_state:
            return

        if self.current_tick is None:
            self._invariant("record_transition called outside an active tick")
            return

        pos = (x, y)
        prior_changes = self.state_changes[pos]
        if prior_changes and not allow_multiple:
            self._invariant(
                "cell changed state more than once in the same tick: "
                f"tick={self.current_tick} pos={pos} first={prior_changes[-1].new_state} "
                f"second={new_state}"
            )

        record = StateChangeRecord(
            tick=self.current_tick,
            position=pos,
            previous_state=previous_state,
            new_state=new_state,
            cause=cause,
            phase=phase,
            visible_live_neighbor_count=count_visible_live_neighbors(grid, x, y),
            source_organism_id=source_organism_id,
            near_organism_boundary=near_organism_boundary,
        )
        prior_changes.append(record)

        if new_state != CellType.LIVE:
            if previous_state == CellType.LIVE:
                self.live_origins.pop(pos, None)
            return

        if cause not in _VALID_BIRTH_CAUSES:
            self._invariant(
                f"invalid live-cell cause {cause!r} at tick={self.current_tick} pos={pos}"
            )

        if pos in self.live_births:
            self._invariant(
                "live cell received multiple birth records in one tick: "
                f"tick={self.current_tick} pos={pos}"
            )

        self.live_births[pos] = record
        self.live_origins[pos] = record
        self._log_birth(record)

        if cause == UNKNOWN:
            self._invariant(
                f"live cell appeared with cause unknown at tick={self.current_tick} pos={pos}"
            )

        if phase == "D3" and source_organism_id is not None:
            self.d3_live_writes[source_organism_id].add(pos)
            if not near_organism_boundary:
                self._invariant(
                    "D3 wrote a live cell away from the organism boundary: "
                    f"tick={self.current_tick} organism_id={source_organism_id} pos={pos}"
                )

    def set_d3_write_limit(self, organism_id: int, allowed_writes: int) -> None:
        """Register the maximum legal number of D3 live writes for an organism."""
        if not self.enabled:
            return
        self.d3_write_limits[organism_id] = allowed_writes

    def check_d3_write_limits(self) -> None:
        """Validate per-organism D3 write counts."""
        if not self.enabled:
            return

        for organism_id, allowed_writes in self.d3_write_limits.items():
            actual_writes = len(self.d3_live_writes.get(organism_id, set()))
            if actual_writes > allowed_writes:
                self._invariant(
                    "D3 created more live cells than allowed for one organism in a tick: "
                    f"tick={self.current_tick} organism_id={organism_id} "
                    f"actual={actual_writes} allowed={allowed_writes}"
                )

    def record_new_organism(self, organism: Organism) -> None:
        """Log the provenance of a newly detected organism."""
        if not self.enabled or self.current_tick is None:
            return

        cell_records: list[OrganismAppearanceCellRecord] = []
        explainable_cells: set[tuple[int, int]] = set()
        for pos in sorted(organism.cells, key=lambda cell: (cell[1], cell[0])):
            birth = self.live_births.get(pos)
            if birth is not None:
                if birth.phase == "D3":
                    source = "D3 writes this tick"
                elif birth.phase == "D2":
                    source = "D2 births this tick"
                else:
                    source = "write this tick"
                cell_records.append(
                    OrganismAppearanceCellRecord(
                        position=pos,
                        source=source,
                        cause=birth.cause,
                    )
                )
                explainable_cells.add(pos)
                continue

            if pos in self.previous_live_cells:
                prior_origin = self.live_origins.get(pos)
                cell_records.append(
                    OrganismAppearanceCellRecord(
                        position=pos,
                        source="pre-existing live cells",
                        cause=None if prior_origin is None else prior_origin.cause,
                        origin_tick=None if prior_origin is None else prior_origin.tick,
                        origin_phase=None if prior_origin is None else prior_origin.phase,
                    )
                )
                explainable_cells.add(pos)
                continue

            cell_records.append(
                OrganismAppearanceCellRecord(
                    position=pos,
                    source="unknown",
                )
            )

        if explainable_cells != organism.cells or not _are_cells_connected(explainable_cells):
            self._invariant(
                "new organism was created from cells not connected via previous live cells "
                "plus current legal births: "
                f"tick={self.current_tick} organism_id={organism.organism_id}"
            )

        appearance = OrganismAppearanceRecord(
            organism_id=organism.organism_id,
            tick=self.current_tick,
            cells=tuple(cell_records),
        )
        self.organism_appearances.append(appearance)
        self._log_organism_appearance(appearance)

    def finalize_tick(self, grid: Grid) -> None:
        """Validate that every newly live cell is traceable."""
        if not self.enabled or self.current_tick is None:
            return

        final_live_cells = _live_cells(grid)
        for pos in sorted(final_live_cells - self.previous_live_cells, key=lambda cell: (cell[1], cell[0])):
            birth = self.live_births.get(pos)
            if birth is None:
                self._invariant(
                    f"live cell appeared without recorded cause at tick={self.current_tick} pos={pos}"
                )
                continue

            if birth.cause == UNKNOWN:
                self._invariant(
                    f"live cell appeared with cause unknown at tick={self.current_tick} pos={pos}"
                )

    @property
    def violation_count(self) -> int:
        return len(self.violations)

    def _log_birth(self, record: StateChangeRecord) -> None:
        self._log(
            "[birth-debug][birth] "
            f"tick={record.tick} pos={record.position} "
            f"prev={_cell_name(record.previous_state)} new={_cell_name(record.new_state)} "
            f"cause={record.cause} visible_live_neighbors={record.visible_live_neighbor_count} "
            f"source_organism_id={record.source_organism_id} "
            f"near_boundary={record.near_organism_boundary} phase={record.phase}"
        )

    def _log_organism_appearance(self, appearance: OrganismAppearanceRecord) -> None:
        parts = [
            f"{cell.position}:{cell.source}"
            + (f"/{cell.cause}" if cell.cause else "")
            + (
                f"@{cell.origin_tick}:{cell.origin_phase}"
                if cell.origin_tick is not None and cell.origin_phase is not None
                else ""
            )
            for cell in appearance.cells
        ]
        self._log(
            "[birth-debug][organism] "
            f"tick={appearance.tick} organism_id={appearance.organism_id} "
            f"cells=[{', '.join(parts)}]"
        )

    def _invariant(self, message: str) -> None:
        self.violations.append(message)
        self._log(f"[birth-debug][error] {message}")
        if self.strict:
            raise RuntimeError(message)

    def _log(self, message: str) -> None:
        if self.enabled:
            print(message, file=self.stream)


def is_adjacent_to_organism_boundary(
    organism_cells: set[tuple[int, int]],
    pos: tuple[int, int],
) -> bool:
    """Return True when pos is adjacent to at least one organism cell."""
    x, y = pos
    for dx, dy in _NEIGHBOR_OFFSETS:
        if (x + dx, y + dy) in organism_cells:
            return True
    return False


def _live_cells(grid: Grid) -> set[tuple[int, int]]:
    cells: set[tuple[int, int]] = set()
    for y in range(grid.height):
        for x in range(grid.width):
            if grid.get(x, y) == CellType.LIVE:
                cells.add((x, y))
    return cells


def _cell_name(value: int) -> str:
    try:
        return CellType(value).name
    except ValueError:
        return str(value)


def _are_cells_connected(cells: set[tuple[int, int]]) -> bool:
    if not cells:
        return False

    start = next(iter(cells))
    queue: deque[tuple[int, int]] = deque([start])
    seen = {start}
    while queue:
        x, y = queue.popleft()
        for dx, dy in _NEIGHBOR_OFFSETS:
            neighbor = (x + dx, y + dy)
            if neighbor in cells and neighbor not in seen:
                seen.add(neighbor)
                queue.append(neighbor)
    return seen == cells