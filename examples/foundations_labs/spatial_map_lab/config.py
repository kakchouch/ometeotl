"""SimConfig — tunable parameters for the spatial map lab."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SimConfig:
    """All knobs for the spatial map simulation.

    Attributes
    ----------
    grid_cols:
        Number of zone columns in the grid.
    grid_rows:
        Number of zone rows in the grid.
    zone_size:
        Width and height of each zone in world units.
    zone_gap:
        Gap between adjacent zones in world units.
        0 means zones share a boundary (touching).
        Positive values create gaps; actors can still traverse them
        because adjacency_tolerance = zone_gap + epsilon.
    num_actors:
        Number of actors placed at simulation start.
    seed:
        RNG seed for reproducibility. None means random.
    move_probability:
        Per-tick probability that a given actor moves to an adjacent zone.
    max_ticks:
        Hard stop for auto-run (0 = unlimited).
    """

    grid_cols: int = 5
    grid_rows: int = 4
    zone_size: float = 100.0
    zone_gap: float = 5.0
    num_actors: int = 12
    seed: int | None = 42
    move_probability: float = 0.7
    max_ticks: int = 0

    def validate(self) -> None:
        """Raise ValueError if any parameter is out of range."""
        if self.grid_cols < 2:
            raise ValueError("grid_cols must be >= 2")
        if self.grid_rows < 2:
            raise ValueError("grid_rows must be >= 2")
        if self.grid_cols > 12:
            raise ValueError("grid_cols must be <= 12")
        if self.grid_rows > 12:
            raise ValueError("grid_rows must be <= 12")
        if self.zone_size <= 0:
            raise ValueError("zone_size must be > 0")
        if self.zone_gap < 0:
            raise ValueError("zone_gap must be >= 0")
        if self.num_actors < 1:
            raise ValueError("num_actors must be >= 1")
        if not 0.0 <= self.move_probability <= 1.0:
            raise ValueError("move_probability must be in [0, 1]")
        if self.max_ticks < 0:
            raise ValueError("max_ticks must be >= 0")

    def to_dict(self) -> dict:
        """Serialise to a plain dict for the JSON API."""
        return {
            "grid_cols": self.grid_cols,
            "grid_rows": self.grid_rows,
            "zone_size": self.zone_size,
            "zone_gap": self.zone_gap,
            "num_actors": self.num_actors,
            "seed": self.seed,
            "move_probability": self.move_probability,
            "max_ticks": self.max_ticks,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SimConfig":
        """Build a SimConfig from a plain dict (e.g. JSON body from the UI)."""
        allowed = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in d.items() if k in allowed}
        return cls(**filtered)
