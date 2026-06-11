"""SimConfig — all configurable parameters for the multi-agent simulation.

Every parameter has a safe default so the simulation can run out of the box.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SimConfig:
    """All tunable knobs for the multi-agent graph simulation.

    Attributes
    ----------
    num_nodes:
        Total number of nodes in the graph.
    num_factions:
        Number of starting factions (must be <= num_nodes).
    seed:
        RNG seed for reproducibility.  None means random each run.
    min_spice_flow:
        Minimum per-tick resource flow a node can generate (inclusive).
    max_spice_flow:
        Maximum per-tick resource flow a node can generate (inclusive).
    graph_density:
        Approximate fraction of possible edges to include (0.1 – 1.0).
        A minimum spanning-tree is always added first to guarantee connectivity.
    flip_threshold:
        Total cumulative pressure (resource units) a faction must spend
        against a neutral/enemy node before it flips ownership.
    drift_threshold_fraction:
        Fraction of genome bits that may differ before a node seceeds.
        E.g. 0.5 on a 16-bit genome means ≥ 8 bits different triggers secession.
    genome_length:
        Number of bits in each faction's genome bitfield.
    mutation_rate:
        Probability per tick that a given controlled node mutates one random bit
        of its local genome copy.  Actual rate is further weighted by 1/(bfs_depth+1)
        so nodes far from the capital drift more.
    max_ticks:
        Hard stop for auto-run (0 = unlimited).
    layout:
        'ring' or 'grid' — determines how node positions are computed for the UI.
    graph_mode:
        'uniform' for generic random graph, 'geographic' for clustered map-like
        topology with wider regions and chokepoints.
    perception_mode:
        'full' for omniscience (Lab 2 mode), 'limited' for fog-of-war (Lab 3 mode).
    """

    num_nodes: int = 14
    num_factions: int = 3
    seed: int | None = 42
    min_spice_flow: int = 1
    max_spice_flow: int = 8
    graph_density: float = 0.25
    flip_threshold: float = 20.0
    drift_threshold_fraction: float = 0.5
    genome_length: int = 16
    mutation_rate: float = 0.05
    max_ticks: int = 0
    layout: str = "ring"  # "ring" | "grid"
    graph_mode: str = "uniform"  # "uniform" | "geographic"
    perception_mode: str = "limited"  # "full" | "limited"

    # ------------------------------------------------------------------ #
    # Derived / validated accessors                                         #
    # ------------------------------------------------------------------ #

    @property
    def drift_threshold_bits(self) -> int:
        """Minimum Hamming distance (bits) that triggers a secession event."""
        return max(1, round(self.drift_threshold_fraction * self.genome_length))

    def validate(self) -> None:
        """Raise ValueError if any parameter is out of range."""
        if self.num_nodes < 2:
            raise ValueError("num_nodes must be >= 2")
        if self.num_factions < 1:
            raise ValueError("num_factions must be >= 1")
        if self.num_factions > self.num_nodes:
            raise ValueError("num_factions must be <= num_nodes")
        if self.min_spice_flow < 1:
            raise ValueError("min_spice_flow must be >= 1")
        if self.max_spice_flow < self.min_spice_flow:
            raise ValueError("max_spice_flow must be >= min_spice_flow")
        if not 0.0 < self.graph_density <= 1.0:
            raise ValueError("graph_density must be in (0, 1]")
        if self.flip_threshold <= 0:
            raise ValueError("flip_threshold must be > 0")
        if not 0.0 < self.drift_threshold_fraction <= 1.0:
            raise ValueError("drift_threshold_fraction must be in (0, 1]")
        if self.genome_length < 1:
            raise ValueError("genome_length must be >= 1")
        if not 0.0 <= self.mutation_rate <= 1.0:
            raise ValueError("mutation_rate must be in [0, 1]")
        if self.max_ticks < 0:
            raise ValueError("max_ticks must be >= 0")
        if self.layout not in ("ring", "grid"):
            raise ValueError("layout must be 'ring' or 'grid'")
        if self.graph_mode not in ("uniform", "geographic"):
            raise ValueError("graph_mode must be 'uniform' or 'geographic'")
        if self.perception_mode not in ("full", "limited"):
            raise ValueError("perception_mode must be 'full' or 'limited'")

    @classmethod
    def from_dict(cls, d: dict) -> "SimConfig":
        """Build a SimConfig from a plain dict (e.g. JSON body from UI)."""
        allowed = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in d.items() if k in allowed}
        return cls(**filtered)

    def to_dict(self) -> dict:
        """Serialise to a plain dict for the JSON API."""
        return {
            "num_nodes": self.num_nodes,
            "num_factions": self.num_factions,
            "seed": self.seed,
            "min_spice_flow": self.min_spice_flow,
            "max_spice_flow": self.max_spice_flow,
            "graph_density": self.graph_density,
            "flip_threshold": self.flip_threshold,
            "drift_threshold_fraction": self.drift_threshold_fraction,
            "genome_length": self.genome_length,
            "mutation_rate": self.mutation_rate,
            "max_ticks": self.max_ticks,
            "layout": self.layout,
            "graph_mode": self.graph_mode,
            "perception_mode": self.perception_mode,
            "drift_threshold_bits": self.drift_threshold_bits,
        }
