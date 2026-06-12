# spatial primitives and abstractions
from .bounding_box import BoundingBox
from .coordinate_system import (
    CARTESIAN_2D,
    CARTESIAN_3D,
    GRID,
    WGS84,
    CoordinateKind,
    CoordinateSystem,
)
from .coordinates import Coordinate2D, Coordinate3D, GeoCoordinate, GridCell
from .geometric_space import GeometricSpace
from .geometry import Geometry
from .relation_derivation import derive_space_relations
from .spatial_backend import SpatialBackend
from .spatial_extent import SpatialExtent
from .spatial_index import SpatialIndex
from .spatial_map import SpatialMap

__all__ = [
    # Coordinate value types
    "Coordinate2D",
    "Coordinate3D",
    "GeoCoordinate",
    "GridCell",
    # Coordinate systems
    "CoordinateKind",
    "CoordinateSystem",
    "CARTESIAN_2D",
    "CARTESIAN_3D",
    "WGS84",
    "GRID",
    # Geometry protocol and pure-Python primitive
    "Geometry",
    "BoundingBox",
    # Adapter protocols
    "SpatialIndex",
    "SpatialBackend",
    # Space + geometry composition
    "GeometricSpace",
    # Object positioning
    "SpatialExtent",
    "SpatialMap",
    # Relation derivation bridge
    "derive_space_relations",
]
