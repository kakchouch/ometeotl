# ometeotl_foundations: Priority Layers Analysis

## Current State
- 8 empty directories: agents/, gametheory/, networks/, perception/, rules/, spatial/, stochastic/, temporal/
- **ometeotl_foundations is skeleton; mostly unused**
- All pattern code lives in examples/labs

## What Labs 3–10 Reinvent (Duplication Analysis)

### **CRITICAL — Every single lab reimplements these:**

| Pattern | Labs | Per-Lab LOC | Total Duplication | Should Go To |
|---------|------|-----------|-------------------|-------------|
| BehaviorProfile class | 3–10 (8) | 30 | **240** | `agents/` |
| Genome operations (random, mutate) | 3–10 (8) | 20 | **160** | `stochastic/` |
| step() orchestration | 3–10 (8) | 50 | **400** | `temporal/` |
| _mutate_and_check_secession() | 3–10 (8) | 40 | **320** | `agents/` |
| check_win_condition() | 3–10 (8) | 30 | **240** | `gametheory/` |
| Offense/defense scoring | 3–10 (8) | 100 | **800** | `gametheory/` |
| **Subtotal Critical** | | | **2,160 lines** | |

### **HIGH PRIORITY — Most labs reinvent these:**

| Pattern | Labs | Per-Lab LOC | Total | Should Go To |
|---------|------|-----------|-------|-------------|
| Conquest/pressure logic | 3–10 (8) | 150 | **1,200** | `rules/` or `gametheory/` |
| Transport/move planning | 4–10 (7) | 80 | **560** | `rules/` |
| Relation adjacency queries | 6–10 (5) | 30 | **150** | `networks/` |
| Secession/emergence conditions | 5–10 (6) | 50 | **300** | `agents/` |
| **Subtotal High** | | | **2,210 lines** | |

### **TOTAL DUPLICATION ADDRESSABLE: ~4,370 lines of code**

---

## Recommended ometeotl_foundations Layers

### **Priority 1: UNBLOCK MOST LABS** (implement first 4)

#### **1️⃣ `agents/` — Actor Models & Behavior Patterns**

**What's in labs:**
```python
# Every lab reimplements:
class BehaviorProfile:
    engagement_threshold: float
    concentration: float
    liquidity_preference: float
    objective_bias: float
    centralization: float

def _random_genome(length: int, rng) -> list[int]:
    return [rng.randint(0, 1) for _ in range(length)]

def _mutate_genome(genome: list[int], rng) -> list[int]:
    idx = rng.randrange(len(genome))
    new = genome[:]
    new[idx] = 1 - new[idx]
    return new

def _mutate_and_check_secession(state):
    # Check if node genome drifts from faction genome
    # If so, spawn new faction
```

**Proposed layer:**
- `BehaviorProfile` base class (parameterizable: E, C, L, O, Z or custom)
- `ActorGenome` abstraction (bit vector + operations)
- `GenomeOperations`: random, mutate, hamming_distance, drift_detection
- `ActorBirth`, `ActorElimination` events
- `EmergenceRule`: conditions for new actors spawning (e.g., secession via drift)
- `ActorArchetype`: predefined behavior patterns (aggressive, defensive, balanced)

**Value:** Removes **720 lines** (BehaviorProfile + genome ops × 8 labs)

---

#### **2️⃣ `gametheory/` — Scoring, Utilities, Victory**

**What's in labs:**
```python
# Every lab reimplements:
def compute_offense_defense_scores(state, faction):
    """Build offense and defense scores for each border node."""
    # 1. Compute how much pressure we can apply
    # 2. Compute what threats we face
    # 3. Return priority targets for expand / defend

def check_win_condition(state):
    """Set state.game_over and state.winner_id if a win condition is met."""
    for faction in state.active_factions():
        if len(nodes) == len(state.nodes):
            state.game_over = True
            state.winner_id = faction.faction_id
            return
    # Winner by most nodes
    if state.tick >= state.config.max_ticks:
        best = max(...)
        state.game_over = True
        state.winner_id = best.faction_id
```

**Proposed layer:**
- `UtilityFunction`: Maps metrics → scalar utility
- `ScoringSystem`: Offense, defense, strategic value computation
- `VictoryCondition` base class + common implementations:
  - `DominationVictory`: Control all spaces
  - `MajorityVictory`: Control > 50%
  - `TickLimitVictory`: Max ticks reached
  - `EliminationVictory`: Last faction standing
- `GameEvaluator`: Compute game state utility for all actors
- `StrategicValue`: Evaluate action/target value

**Value:** Removes **1,040 lines** (scoring + win condition × 8 labs)

---

#### **3️⃣ `temporal/` — Tick Orchestration & Phase Ordering**

**What's in labs:**
```python
# Every lab reimplements:
def step(state: SimState) -> None:
    """Execute one simulation tick."""
    # Phase 1: Planning
    _plan_moves(state)
    _plan_centralization(state)
    
    # Phase 2: Execution
    _reset_link_usage(state)
    _execute_transport(state)
    _apply_conquest(state)
    
    # Phase 3: Resource management
    _collect_income(state)
    
    # Phase 4: Evolution
    _mutate_and_check_secession(state)
    
    # Phase 5: Check end condition
    check_win_condition(state)
    
    state.tick += 1
```

**Proposed layer:**
- `SimulationPhase` enum (PLANNING, EXECUTION, COLLECTION, EVOLUTION, EVALUATION)
- `PhaseOrchestrator`: Manages tick sequencing
  - Allows customizing phase order
  - Executes callbacks per phase
  - Handles phase-specific validation
- `TickContext`: Snapshot of tick state for phase callbacks
- `TickScheduler`: Multi-stage phase executor

**Value:** Removes **400 lines** (step orchestration × 8 labs)

---

#### **4️⃣ `rules/` — Rule Evaluation Framework**

**What's in labs:**
```python
# Every lab reimplements conquest/pressure rules differently:
def _apply_conquest(state):
    flipped_nodes = []
    for node in state.nodes.values():
        if node.pressure_accumulated > flip_threshold:
            old_owner = node.owner_id
            node.owner_id = max_pressure_attacker(node)
            # Apply consequences
    return flipped_nodes
```

**Proposed layer:**
- `Rule` base class: Evaluable, applicable rules
- `ConquistRule`: Pressure-based ownership transfer
- `TransportRule`: Logistics, capacity, cost models
- `TributeRule`: Vassal payment systems
- `RuleBook`: Ordered rule evaluation (conflict resolution)
- `RuleEvaluator`: Check if rules apply, compute effects
- `RuleEffect`: Reusable consequence models

**Value:** Removes **1,200 lines** (conquest + transport + other rules × 8 labs)

---

### **Priority 2: ENABLE PATTERN REUSE** (implement next 4)

#### **5️⃣ `stochastic/` — Probabilistic Models & Sampling**

**What's in labs:**
```python
# Every lab reimplements:
def _random_genome(length, rng):
    return [rng.randint(0, 1) for _ in range(length)]

def _mutate_genome(genome, rng):
    idx = rng.randrange(len(genome))
    new = genome[:]
    new[idx] = 1 - new[idx]
    return new

def _hamming_distance(a, b):
    return sum(x != y for x, y in zip(a, b))
```

**Proposed layer:**
- `RandomGenome`: Factory for random bit vectors
- `GenomeMutation`: Bit flip, Hamming distance, drift detection
- `StochasticSampler`: Weighted random selection
- `NoiseInjection`: Add uncertainty to signals
- `ProbabilityDistribution`: Common distributions (uniform, weighted, etc.)

**Value:** Removes **160 lines** (genome ops × 8 labs)

---

#### **6️⃣ `networks/` — Graph Analysis & Topology**

**What's in labs:**
```python
# Labs implement graph queries manually:
def neighbors_of(self, node_id):
    return self.relation_graph.neighbors_of(node_id)

def border_targets_for(self, faction_id):
    """Return nodes adjacent to faction's territory but not owned by it."""
    owned = set(self.nodes_owned_by(faction_id))
    targets = set()
    for nid in owned:
        for nb in self.neighbors_of(nid):
            if self.nodes[nb].owner_id != faction_id:
                targets.add(nb)
    return sorted(targets)

def _bfs_distances_state(state, source):
    """BFS over the relation graph."""
    # Manual BFS implementation
```

**Proposed layer:**
- `NetworkAnalyzer`: Connectivity, reachability, bottlenecks
- `ConnectivityMetrics`: Fragmentation, clusters, bridges
- `FlowAnalysis`: Bottleneck identification, capacity analysis
- `PathFinding`: Shortest path, route analysis
- `GraphProperty`: Centrality, clustering coefficient
- `GeographicRegion`: Region definition and border detection

**Value:** Removes **150 lines** (graph queries × 5–8 labs)

---

#### **7️⃣ `spatial/` — Geographic & Adjacency Models**

**What's in labs:**
```python
# Labs implement geography ad-hoc:
# Lab 9: graph_gen.py has geographic topology generation
# But no reusable spatial abstraction

class Node:
    x: float
    y: float
    # No distance-based adjacency, no terrain model
```

**Proposed layer:**
- `SpatialModel` base class
- `EuclideanSpatial`: 2D distance-based adjacency
- `GridSpatial`: Hex grid or square grid
- `RegionalSpatial`: Region-based topology
- `TerrainCost`: Movement/adjacency cost by terrain type
- `DistanceMetric`: Compute spatial distance
- `GeographyGenerator`: Pangea, continents, archipelago presets

**Value:** Enables **future extensibility** (not critical for current labs)

---

#### **8️⃣ `perception/` — Enhanced Observation Models**

**What's in labs:**
```python
# Lab 3, 10 implement perception partially
# But no reusable observation abstraction

class FactionCoverageRule(CoverageRule):
    """Coverage rule that includes only spaces owned by a faction."""
    # Already partially in core, but needs enhancement
```

**Proposed layer:**
- `ObservationModel` base class
- `NoiseModel`: Inject uncertainty into observations
- `InformationDecay`: Forget old information
- `SensorType`: Different sensor capabilities
- `SignalQuality`: Trust/confidence in observations
- `ObservationBias`: Systematic misperception

**Value:** Enables **imperfect information games** (not critical for current labs, but mentioned in Specs)

---

### **Priority 3: ADVANCED FEATURES** (implement if needed)

#### **9️⃣ `temporal/` — Advanced Time Models

**Proposed:**
- Event scheduling (not just tick-based)
- Asynchronous actors (different speeds)
- Historical tracking (full audit trail)
- Temporal constraints and dependencies

**Value:** Enables **complex temporal dynamics** (beyond current labs)

---

## Priority Matrix

| Layer | Labs Affected | Duplication | Implementation Effort | ROI | Priority |
|-------|---------------|-------------|----------------------|-----|----------|
| agents/ | 8 | 720 LOC | Medium | **HIGH** | **1** |
| gametheory/ | 8 | 1,040 LOC | Medium | **HIGH** | **1** |
| temporal/ | 8 | 400 LOC | Low | **HIGH** | **1** |
| rules/ | 8 | 1,200 LOC | High | **MEDIUM** | **2** |
| stochastic/ | 8 | 160 LOC | Low | **MEDIUM** | **2** |
| networks/ | 5–8 | 150 LOC | Medium | **MEDIUM** | **2** |
| spatial/ | 2–3 | 0 LOC (new) | High | **LOW** | **3** |
| perception/ | 2–3 | 0 LOC (in core) | Medium | **LOW** | **3** |

---

## Implementation Recommendation

### **Phase 1: Foundation Layers (Priority 1)**
1. Implement `agents/` (BehaviorProfile, Genome operations)
2. Implement `gametheory/` (Scoring, Victory conditions)
3. Implement `temporal/` (Tick orchestration)
4. Pilot with **Lab 5** (Behavior Sim) — simple, benefits immediately

### **Phase 2: Pattern Layers (Priority 2)**
5. Implement `rules/` (Conquest, Transport, Tribute rules)
6. Implement `stochastic/` (Random sampling, Mutation)
7. Implement `networks/` (Graph analysis, Connectivity)
8. Migrate **Labs 6→8→9→10** incrementally

### **Phase 3: Advanced Layers (Priority 3)**
9. Implement `spatial/` (Geographic models)
10. Enhance `perception/` (Noise, decay, bias)
11. Future labs can use these for new features

---

## Key Numbers

- **Total addressable duplication:** 4,370 lines
- **Priority 1 implementation:** ~500 lines of foundations code
- **ROI:** 500 lines saved × 8 labs = **4,000 lines consolidated**
- **ROI ratio:** 8:1

---

## Critical Insight

**ometeotl_foundations is 90% empty.** The labs themselves represent the "foundation abstractions" that should be extracted into the framework:

- **BehaviorProfile** is not domain-specific; it's a universal agent personality model
- **Genome operations** apply to any evolutionary system
- **Tick orchestration** applies to any turn-based game
- **Scoring systems** apply to any multi-agent competition
- **Win conditions** apply to any game

By extracting these into ometeotl_foundations, we make them available to the next 10 labs without reinvention.
