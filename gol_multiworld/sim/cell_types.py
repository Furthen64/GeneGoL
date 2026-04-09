from enum import IntEnum


class CellType(IntEnum):
    EMPTY = 0
    LIVE = 1
    FOOD = 2
    WALL = 3
    TOXIC = 4


# Default colors for each cell type (R, G, B)
CELL_COLORS: dict[int, tuple[int, int, int]] = {
    CellType.EMPTY: (20, 20, 30),
    CellType.LIVE: (100, 220, 100),
    CellType.FOOD: (220, 200, 50),
    CellType.WALL: (120, 120, 130),
    CellType.TOXIC: (200, 50, 180),
}
