from enum import Enum


class LayoutArchetype(str, Enum):
    CENTERED_ANCHOR = "centered anchor composition"
    DIAGONAL_EDITORIAL = "diagonal editorial spread"
    RADIAL_OUTFIT = "radial outfit spread"
    CATALOG_GRID = "catalog grid-like arrangement"
    PRACTICAL_BOARD = "practical dressing board"
