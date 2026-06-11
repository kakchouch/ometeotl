"""SimConfig — all configurable parameters for the multi-agent simulation.

Extends Lab 11 (Technology) with Lab 12: Devastation.

Every parameter has a safe default so the simulation can run out of the box.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SimConfig:
    # ---- Inherited from Lab 11 ----
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
    layout: str = "ring"
    graph_mode: str = "geographic"
    geography_preset: str = "continents"
    layout_min_node_distance: float = 0.13
    perception_mode: str = "limited"
    initial_node_spice: float = 5.0
    min_link_flow: float = 3.0
    max_link_flow: float = 12.0
    max_spice_move_fraction: float = 0.7
    transport_gas_fee: float = 0.05
    transport_base_cost: float = 1.0
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
    # Tech pipeline (Lab 11)
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
    tech_rnd_base_cost: float = 2.0
    tech_rnd_history_window: int = 5
    tech_diplo_perception_effect: float = 0.3
    tech_cohe_threshold_bonus: float = 0.3
    tech_logi_cost_reduction: float = 0.5
    tech_reserve_reference: float = 50.0
    tech_investment_scale: float = 0.002
    # Lab 11 Change 1 — Logistics stock cap
    base_stock_cap: float = 50.0
    logi_stock_cap_bonus: float = 100.0
    # Lab 11 Change 2 — Cohesion Hamming threshold decay
    cohe_hamming_bonus: float = 5.0
    cohe_hamming_decay: float = 4.0
    min_hamming_threshold: float = 1.0
    # Lab 11 Change 3 — Diplomacy gap bias
    diplo_bias_strength: float = 0.3

    # ---- Lab 12: Devastation ----
    devastation_window_size: int = 10
    # Rolling window (ticks) used for flip_count_in_window audit field.
    devastation_flip_increment: float = 0.3
    # Added to devastation on each ownership flip. Clamped to [0, 1].
    devastation_recovery_rate: float = 0.01
    # Subtracted from devastation each stable (non-flip) tick. Floored at 0.
    devastation_cap_penalty: float = 0.5
    # Fraction of logi-based stock cap lost at devastation=1.
    # effective_cap = logi_cap * (1 - devastation * cap_penalty), floor at min_stock_cap.
    devastation_production_penalty: float = 0.5
    # Fraction of base_node_production lost at devastation=1.
    # effective_prod = base_node_production * (1 - devastation * prod_penalty), floor at min_node_production.
    devastation_attractiveness_penalty: float = 0.7
    # Multiplied by perceived devastation to discount conquest attractiveness.
    # attractiveness = perceived_stock * perceived_production * (1 - perceived_devas * penalty)
    base_node_production: float = 2.0
    # Flat spice production added to each owned node per tick (before devastation degradation).
    # Separate from spice_flow (which is not degraded by devastation).
    min_stock_cap: float = 1.0
    # Floor for effective_stock_cap; cannot drop below this even at full devastation.
    min_node_production: float = 0.0
    # Floor for the devastation-degraded component of production.

    # ------------------------------------------------------------------ #
    # Derived / validated accessors                                        #
    # ------------------------------------------------------------------ #

    @property
    def drift_threshold_bits(self) -> int:
        return max(1, round(self.drift_threshold_fraction * self.genome_length))

    def validate(self) -> None:
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
            raise ValueError("geography_preset must be 'pangea', 'continents', or 'archipelago'")
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
            raise ValueError("behavior_engagement_min must be <= behavior_engagement_max")
        if not 0.0 <= self.behavior_concentration_min <= 1.0:
            raise ValueError("behavior_concentration_min must be in [0, 1]")
        if not 0.0 <= self.behavior_concentration_max <= 1.0:
            raise ValueError("behavior_concentration_max must be in [0, 1]")
        if self.behavior_concentration_min > self.behavior_concentration_max:
            raise ValueError("behavior_concentration_min must be <= behavior_concentration_max")
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
            raise ValueError("behavior_centralization_min must be <= behavior_centralization_max")
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
            "tech_alpha_weight_pressure_diplo", "tech_alpha_weight_pressure_logi",
            "tech_alpha_weight_relation_inv_diplo", "tech_alpha_weight_min_relation_inv_diplo",
            "tech_alpha_weight_owned_fraction_inv_diplo", "tech_alpha_weight_owned_fraction_cohe",
            "tech_alpha_weight_owned_fraction_logi", "tech_alpha_weight_disconnected_cohe",
            "tech_alpha_weight_known_ratio_inv_logi", "tech_alpha_weight_known_ratio_inv_diplo",
        ):
            if getattr(self, _wname) < 0.0:
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
        if self.tech_investment_scale <= 0.0:
            raise ValueError("tech_investment_scale must be > 0")
        if self.base_stock_cap < 0.0:
            raise ValueError("base_stock_cap must be >= 0")
        if self.logi_stock_cap_bonus < 0.0:
            raise ValueError("logi_stock_cap_bonus must be >= 0")
        if self.cohe_hamming_bonus < 0.0:
            raise ValueError("cohe_hamming_bonus must be >= 0")
        if self.cohe_hamming_decay < 0.0:
            raise ValueError("cohe_hamming_decay must be >= 0")
        if self.min_hamming_threshold < 1.0:
            raise ValueError("min_hamming_threshold must be >= 1")
        if self.diplo_bias_strength < 0.0:
            raise ValueError("diplo_bias_strength must be >= 0")
        # Lab 12 devastation params
        if self.devastation_window_size < 1:
            raise ValueError("devastation_window_size must be >= 1")
        if not 0.0 <= self.devastation_flip_increment <= 1.0:
            raise ValueError("devastation_flip_increment must be in [0, 1]")
        if not 0.0 <= self.devastation_recovery_rate <= 1.0:
            raise ValueError("devastation_recovery_rate must be in [0, 1]")
        if not 0.0 <= self.devastation_cap_penalty <= 1.0:
            raise ValueError("devastation_cap_penalty must be in [0, 1]")
        if not 0.0 <= self.devastation_production_penalty <= 1.0:
            raise ValueError("devastation_production_penalty must be in [0, 1]")
        if not 0.0 <= self.devastation_attractiveness_penalty <= 1.0:
            raise ValueError("devastation_attractiveness_penalty must be in [0, 1]")
        if self.base_node_production < 0.0:
            raise ValueError("base_node_production must be >= 0")
        if self.min_stock_cap < 0.0:
            raise ValueError("min_stock_cap must be >= 0")
        if self.min_node_production < 0.0:
            raise ValueError("min_node_production must be >= 0")

    @classmethod
    def from_dict(cls, d: dict) -> "SimConfig":
        allowed = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in d.items() if k in allowed}
        return cls(**filtered)

    def to_dict(self) -> dict:
        d = {
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
            "tech_investment_scale": self.tech_investment_scale,
            "base_stock_cap": self.base_stock_cap,
            "logi_stock_cap_bonus": self.logi_stock_cap_bonus,
            "cohe_hamming_bonus": self.cohe_hamming_bonus,
            "cohe_hamming_decay": self.cohe_hamming_decay,
            "min_hamming_threshold": self.min_hamming_threshold,
            "diplo_bias_strength": self.diplo_bias_strength,
            # Lab 12
            "devastation_window_size": self.devastation_window_size,
            "devastation_flip_increment": self.devastation_flip_increment,
            "devastation_recovery_rate": self.devastation_recovery_rate,
            "devastation_cap_penalty": self.devastation_cap_penalty,
            "devastation_production_penalty": self.devastation_production_penalty,
            "devastation_attractiveness_penalty": self.devastation_attractiveness_penalty,
            "base_node_production": self.base_node_production,
            "min_stock_cap": self.min_stock_cap,
            "min_node_production": self.min_node_production,
        }
        return d
