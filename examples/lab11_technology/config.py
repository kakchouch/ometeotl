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
    geography_preset:
        Geographic topology preset used when graph_mode='geographic':
        - 'pangea': one large landmass with a few peripheral dead-ends
        - 'continents': several landmasses with few narrow corridors
        - 'archipelago': many smaller landmasses with sparse corridors
    layout_min_node_distance:
        Minimum desired normalized distance between nodes during layout
        readability post-processing. Higher values spread nodes farther apart.
    perception_mode:
        'full' for omniscience (Lab 2 mode), 'limited' for fog-of-war (Lab 3 mode).
    initial_node_spice:
        Initial spice stock stored on each node at simulation start.
    min_link_flow:
        Minimum per-tick transport capacity on any graph link.
    max_link_flow:
        Maximum per-tick transport capacity on any graph link.
    max_spice_move_fraction:
        Max fraction of a node's stock that can be dispatched per tick.
    transport_gas_fee:
        Fraction of spice lost as a proportional transport cost each time spice
        moves across one link (e.g. 0.1 means 10 % of the moved amount is
        destroyed in transit).  Applies per hop, compounding over multi-hop
        routes.
    transport_base_cost:
        Flat spice overhead burned from the source node each time a move order
        is initiated, regardless of the amount shipped.  Acts as a "base gas
        fee" per shipment: many small scattered moves each pay this overhead,
        while one large focused move pays it only once.  Set to 0 to disable.
    behavior_engagement_min / behavior_engagement_max:
        Engagement threshold range (0..1). High values make factions less
        likely to attack without strong upside.
    behavior_concentration_min / behavior_concentration_max:
        Concentration range (0..1). High values focus resources on fewer
        targets; low values spread across multiple fronts.
    behavior_liquidity_min / behavior_liquidity_max:
        Liquidity preference range (0..1). High values conserve stock (low
        spend now); low values spend aggressively each tick.
    behavior_objective_min / behavior_objective_max:
        Objective bias range (0..1). 0 favors defensive/economic reinforcement;
        1 favors offensive territorial pressure.
    behavior_centralization_min / behavior_centralization_max:
        Centralization range (Z, 0..1). High values spend more spice to
        suppress genetic drift at controlled nodes.
    centralization_admin_cost:
        Spice cost per bit corrected by administrative drift suppression.
    relation_initial:
        Initial relation value when two factions first get to know each other.
        Must be in [0, 1].
    relation_growth_rate:
        Base per-tick growth added to known faction relations.
    relation_pressure_impact:
        Relation loss per unit of delivered pressure spice.
    relation_offense_bias:
        Strength of relation impact on offense appetite.
        High relation lowers pressure appetite; low relation raises it.
    allow_disconnected_regions:
        When True and graph_mode='geographic', region bridges are optional,
        allowing initially disconnected maps.
    globalization_link_growth_chance:
        Per-tick chance that one existing link capacity grows by +1.
    globalization_bridge_spawn_chance:
        Per-tick chance that a new 1-capacity link is created between two
        currently disconnected components.

    # ---- Technology investment pipeline (Lab 11) ----
    tech_alpha_weight_pressure_diplo:
        Weight of total_pressure_received signal on α_diplo.
    tech_alpha_weight_pressure_logi:
        Weight of total_pressure_received signal on α_logi.
    tech_alpha_weight_relation_inv_diplo:
        Weight of (1 − mean_relation) signal on α_diplo.
    tech_alpha_weight_min_relation_inv_diplo:
        Weight of (1 − min_relation) spike signal on α_diplo.
    tech_alpha_weight_owned_fraction_inv_diplo:
        Weight of (1 − owned_fraction) signal on α_diplo.
    tech_alpha_weight_owned_fraction_cohe:
        Weight of owned_fraction signal on α_cohe.
    tech_alpha_weight_owned_fraction_logi:
        Weight of owned_fraction signal on α_logi.
    tech_alpha_weight_disconnected_cohe:
        Weight of disconnected_owned ratio signal on α_cohe.
    tech_alpha_weight_known_ratio_inv_logi:
        Weight of (1 − known_ratio) signal on α_logi.
    tech_alpha_weight_known_ratio_inv_diplo:
        Weight of (1 − known_ratio) signal on α_diplo.
    tech_leader_cost_multiplier:
        Extra cost multiplier charged to the faction that leads on a tech axis.
        The leader's effective rubberbanding multiplier is 1 + this value.
    tech_neighbor_acceleration:
        Cost-reduction factor per unit of tech gap behind a border neighbor.
        Applied per axis independently.
    tech_rnd_base_cost:
        Spice cost per unit of investment vector magnitude in step 7.
    tech_rnd_history_window:
        Rolling history window (number of ticks) used for C and Z steps.
    tech_diplo_perception_effect:
        Maximum fraction by which Diplo inflates attacker's perceived relation
        with the Diplo holder (reduces attacker's aggression).
    tech_cohe_threshold_bonus:
        Maximum extra fraction of genome_length added to drift_threshold when
        Cohé = 1. Increases the Hamming distance needed for secession.
    tech_logi_cost_reduction:
        Maximum fraction of transport_gas_fee eliminated when Logi = 1.
    tech_reserve_reference:
        Reference spice level used in step 5 (L spend-rate normalisation).
        A faction holding this much spice will have its investment scaled down
        proportionally to its liquidity_preference.
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
    graph_mode: str = "geographic"  # "uniform" | "geographic"
    geography_preset: str = "continents"  # "pangea" | "continents" | "archipelago"
    layout_min_node_distance: float = 0.13
    perception_mode: str = "limited"  # "full" | "limited"
    initial_node_spice: float = 5.0
    min_link_flow: float = 3.0
    max_link_flow: float = 12.0
    max_spice_move_fraction: float = 0.7
    transport_gas_fee: float = 0.05  # fraction lost per hop (0 = free, 1 = full loss)
    transport_base_cost: float = 1.0  # flat overhead per shipment (punishes scatter)
    behavior_engagement_min: float = 0.2
    behavior_engagement_max: float = 0.8
    behavior_concentration_min: float = 0.2
    behavior_concentration_max: float = 0.8
    behavior_liquidity_min: float = 0.2
    behavior_liquidity_max: float = 0.8
    behavior_objective_min: float = 0.2
    behavior_objective_max: float = 0.8
    behavior_centralization_min: float = 0.2
    behavior_centralization_max: float = 0.8
    centralization_admin_cost: float = 1.0
    relation_initial: float = 0.85
    relation_growth_rate: float = 0.01
    relation_pressure_impact: float = 0.015
    relation_offense_bias: float = 0.6
    allow_disconnected_regions: bool = True
    globalization_link_growth_chance: float = 0.01
    globalization_bridge_spawn_chance: float = 0.005

    # ---- Technology investment pipeline (Lab 11) ----
    tech_alpha_weight_pressure_diplo: float = 0.4
    tech_alpha_weight_pressure_logi: float = 0.3
    tech_alpha_weight_relation_inv_diplo: float = 0.3
    tech_alpha_weight_min_relation_inv_diplo: float = 0.5
    tech_alpha_weight_owned_fraction_inv_diplo: float = 0.2
    tech_alpha_weight_owned_fraction_cohe: float = 0.3
    tech_alpha_weight_owned_fraction_logi: float = 0.3
    tech_alpha_weight_disconnected_cohe: float = 0.8
    tech_alpha_weight_known_ratio_inv_logi: float = 0.3
    tech_alpha_weight_known_ratio_inv_diplo: float = 0.2
    tech_leader_cost_multiplier: float = 1.5
    tech_neighbor_acceleration: float = 0.3
    tech_rnd_base_cost: float = 10.0
    tech_rnd_history_window: int = 5
    tech_diplo_perception_effect: float = 0.3
    tech_cohe_threshold_bonus: float = 0.3
    tech_logi_cost_reduction: float = 0.5
    tech_reserve_reference: float = 50.0

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
        if self.geography_preset not in ("pangea", "continents", "archipelago"):
            raise ValueError(
                "geography_preset must be 'pangea', 'continents', or 'archipelago'"
            )
        if not 0.06 <= self.layout_min_node_distance <= 0.30:
            raise ValueError("layout_min_node_distance must be in [0.06, 0.30]")
        if self.perception_mode not in ("full", "limited"):
            raise ValueError("perception_mode must be 'full' or 'limited'")
        if self.initial_node_spice < 0:
            raise ValueError("initial_node_spice must be >= 0")
        if self.min_link_flow <= 0:
            raise ValueError("min_link_flow must be > 0")
        if self.max_link_flow < self.min_link_flow:
            raise ValueError("max_link_flow must be >= min_link_flow")
        if not 0.0 < self.max_spice_move_fraction <= 1.0:
            raise ValueError("max_spice_move_fraction must be in (0, 1]")
        if not 0.0 <= self.transport_gas_fee < 1.0:
            raise ValueError("transport_gas_fee must be in [0, 1)")
        if self.transport_base_cost < 0.0:
            raise ValueError("transport_base_cost must be >= 0")
        if not 0.0 <= self.behavior_engagement_min <= 1.0:
            raise ValueError("behavior_engagement_min must be in [0, 1]")
        if not 0.0 <= self.behavior_engagement_max <= 1.0:
            raise ValueError("behavior_engagement_max must be in [0, 1]")
        if self.behavior_engagement_min > self.behavior_engagement_max:
            raise ValueError(
                "behavior_engagement_min must be <= behavior_engagement_max"
            )
        if not 0.0 <= self.behavior_concentration_min <= 1.0:
            raise ValueError("behavior_concentration_min must be in [0, 1]")
        if not 0.0 <= self.behavior_concentration_max <= 1.0:
            raise ValueError("behavior_concentration_max must be in [0, 1]")
        if self.behavior_concentration_min > self.behavior_concentration_max:
            raise ValueError(
                "behavior_concentration_min must be <= behavior_concentration_max"
            )
        if not 0.0 <= self.behavior_liquidity_min <= 1.0:
            raise ValueError("behavior_liquidity_min must be in [0, 1]")
        if not 0.0 <= self.behavior_liquidity_max <= 1.0:
            raise ValueError("behavior_liquidity_max must be in [0, 1]")
        if self.behavior_liquidity_min > self.behavior_liquidity_max:
            raise ValueError("behavior_liquidity_min must be <= behavior_liquidity_max")
        if not 0.0 <= self.behavior_objective_min <= 1.0:
            raise ValueError("behavior_objective_min must be in [0, 1]")
        if not 0.0 <= self.behavior_objective_max <= 1.0:
            raise ValueError("behavior_objective_max must be in [0, 1]")
        if self.behavior_objective_min > self.behavior_objective_max:
            raise ValueError("behavior_objective_min must be <= behavior_objective_max")
        if not 0.0 <= self.behavior_centralization_min <= 1.0:
            raise ValueError("behavior_centralization_min must be in [0, 1]")
        if not 0.0 <= self.behavior_centralization_max <= 1.0:
            raise ValueError("behavior_centralization_max must be in [0, 1]")
        if self.behavior_centralization_min > self.behavior_centralization_max:
            raise ValueError(
                "behavior_centralization_min must be <= behavior_centralization_max"
            )
        if self.centralization_admin_cost < 0.0:
            raise ValueError("centralization_admin_cost must be >= 0")
        if not 0.0 <= self.relation_initial <= 1.0:
            raise ValueError("relation_initial must be in [0, 1]")
        if self.relation_growth_rate < 0.0:
            raise ValueError("relation_growth_rate must be >= 0")
        if self.relation_pressure_impact < 0.0:
            raise ValueError("relation_pressure_impact must be >= 0")
        if not 0.0 <= self.relation_offense_bias <= 1.0:
            raise ValueError("relation_offense_bias must be in [0, 1]")
        if not 0.0 <= self.globalization_link_growth_chance <= 1.0:
            raise ValueError("globalization_link_growth_chance must be in [0, 1]")
        if not 0.0 <= self.globalization_bridge_spawn_chance <= 1.0:
            raise ValueError("globalization_bridge_spawn_chance must be in [0, 1]")
        for _wname in (
            "tech_alpha_weight_pressure_diplo",
            "tech_alpha_weight_pressure_logi",
            "tech_alpha_weight_relation_inv_diplo",
            "tech_alpha_weight_min_relation_inv_diplo",
            "tech_alpha_weight_owned_fraction_inv_diplo",
            "tech_alpha_weight_owned_fraction_cohe",
            "tech_alpha_weight_owned_fraction_logi",
            "tech_alpha_weight_disconnected_cohe",
            "tech_alpha_weight_known_ratio_inv_logi",
            "tech_alpha_weight_known_ratio_inv_diplo",
        ):
            _v = getattr(self, _wname)
            if _v < 0.0:
                raise ValueError(f"{_wname} must be >= 0")
        if self.tech_leader_cost_multiplier < 0.0:
            raise ValueError("tech_leader_cost_multiplier must be >= 0")
        if self.tech_neighbor_acceleration < 0.0:
            raise ValueError("tech_neighbor_acceleration must be >= 0")
        if self.tech_rnd_base_cost < 0.0:
            raise ValueError("tech_rnd_base_cost must be >= 0")
        if self.tech_rnd_history_window < 1:
            raise ValueError("tech_rnd_history_window must be >= 1")
        if not 0.0 <= self.tech_diplo_perception_effect <= 1.0:
            raise ValueError("tech_diplo_perception_effect must be in [0, 1]")
        if not 0.0 <= self.tech_cohe_threshold_bonus <= 1.0:
            raise ValueError("tech_cohe_threshold_bonus must be in [0, 1]")
        if not 0.0 <= self.tech_logi_cost_reduction <= 1.0:
            raise ValueError("tech_logi_cost_reduction must be in [0, 1]")
        if self.tech_reserve_reference <= 0.0:
            raise ValueError("tech_reserve_reference must be > 0")

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
            "geography_preset": self.geography_preset,
            "layout_min_node_distance": self.layout_min_node_distance,
            "perception_mode": self.perception_mode,
            "initial_node_spice": self.initial_node_spice,
            "min_link_flow": self.min_link_flow,
            "max_link_flow": self.max_link_flow,
            "max_spice_move_fraction": self.max_spice_move_fraction,
            "transport_gas_fee": self.transport_gas_fee,
            "transport_base_cost": self.transport_base_cost,
            "behavior_engagement_min": self.behavior_engagement_min,
            "behavior_engagement_max": self.behavior_engagement_max,
            "behavior_concentration_min": self.behavior_concentration_min,
            "behavior_concentration_max": self.behavior_concentration_max,
            "behavior_liquidity_min": self.behavior_liquidity_min,
            "behavior_liquidity_max": self.behavior_liquidity_max,
            "behavior_objective_min": self.behavior_objective_min,
            "behavior_objective_max": self.behavior_objective_max,
            "behavior_centralization_min": self.behavior_centralization_min,
            "behavior_centralization_max": self.behavior_centralization_max,
            "centralization_admin_cost": self.centralization_admin_cost,
            "relation_initial": self.relation_initial,
            "relation_growth_rate": self.relation_growth_rate,
            "relation_pressure_impact": self.relation_pressure_impact,
            "relation_offense_bias": self.relation_offense_bias,
            "allow_disconnected_regions": self.allow_disconnected_regions,
            "globalization_link_growth_chance": self.globalization_link_growth_chance,
            "globalization_bridge_spawn_chance": self.globalization_bridge_spawn_chance,
            "drift_threshold_bits": self.drift_threshold_bits,
            "tech_alpha_weight_pressure_diplo": self.tech_alpha_weight_pressure_diplo,
            "tech_alpha_weight_pressure_logi": self.tech_alpha_weight_pressure_logi,
            "tech_alpha_weight_relation_inv_diplo": self.tech_alpha_weight_relation_inv_diplo,
            "tech_alpha_weight_min_relation_inv_diplo": self.tech_alpha_weight_min_relation_inv_diplo,
            "tech_alpha_weight_owned_fraction_inv_diplo": self.tech_alpha_weight_owned_fraction_inv_diplo,
            "tech_alpha_weight_owned_fraction_cohe": self.tech_alpha_weight_owned_fraction_cohe,
            "tech_alpha_weight_owned_fraction_logi": self.tech_alpha_weight_owned_fraction_logi,
            "tech_alpha_weight_disconnected_cohe": self.tech_alpha_weight_disconnected_cohe,
            "tech_alpha_weight_known_ratio_inv_logi": self.tech_alpha_weight_known_ratio_inv_logi,
            "tech_alpha_weight_known_ratio_inv_diplo": self.tech_alpha_weight_known_ratio_inv_diplo,
            "tech_leader_cost_multiplier": self.tech_leader_cost_multiplier,
            "tech_neighbor_acceleration": self.tech_neighbor_acceleration,
            "tech_rnd_base_cost": self.tech_rnd_base_cost,
            "tech_rnd_history_window": self.tech_rnd_history_window,
            "tech_diplo_perception_effect": self.tech_diplo_perception_effect,
            "tech_cohe_threshold_bonus": self.tech_cohe_threshold_bonus,
            "tech_logi_cost_reduction": self.tech_logi_cost_reduction,
            "tech_reserve_reference": self.tech_reserve_reference,
        }
