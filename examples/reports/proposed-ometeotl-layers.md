# Proposed New Layers in ometeotl_core (Summary)

## 6 High-Value Layers Identified Across Labs 3–10

### Priority 1: **UNBLOCK MOST LABS NOW**

#### 1. `model/relations` — Dyadic Actor Relations
- **Problem:** Labs 6–10 each reimplement relation storage (dict-based)
- **Duplication:** ~30 lines per lab for relation_between(), adjust_relation(), relation_key()
- **Proposed:** ActorRelationGraph with multi-space support (diplomacy, kinship, trade)
- **Benefits:** DRY, space-aware, temporal awareness, queryable
- **Value:** Immediate (6 labs need this)

#### 2. `model/transactions` — Resource Transfers (Generic)
- **Problem:** Labs 4–10 reimplement transport logic with identical phases
- **Duplication:** ~200 lines per lab (_plan_moves, _execute_transport, cost models)
- **Proposed:** TransactionIntent + TransactionCost + TransactionExecution classes
- **Benefits:** Handles base cost + proportional cost + dispute loss in one abstraction
- **Value:** Immediate (7 labs need this)

#### 3. `io/event_log` — Structured Event Recording
- **Problem:** Labs 6–10 maintain manual event_log lists (unqueryable strings)
- **Duplication:** Each lab formats events differently
- **Proposed:** GameEvent + EventLog with queryable interface (by type, actor, space, time)
- **Benefits:** Canonical format, AI-exportable, auditable, queryable
- **Value:** Immediate (enables analysis, LLM integration)

### Priority 2: **ENABLE BETTER ANALYSIS**

#### 4. `model/metrics` — Heterogeneous Metric Vectors
- **Problem:** Specs A-21 explicitly requires multi-type metrics; not implemented in core
- **Duplication:** Each lab invents custom scoring (no standard)
- **Proposed:** Metric + MetricVector + MetricHistory classes
- **Benefits:** Supports Specs A-21 (heterogeneous evaluation), normalization, LLM-ready
- **Value:** High (theoretical foundation; enables utility functions)

#### 5. `game/conflict` — Multi-way Dispute Resolution
- **Problem:** Labs 3–10 each reimplement conquest/pressure/flip logic
- **Duplication:** ~150 lines per lab (_apply_conquest with ad-hoc scoring)
- **Proposed:** ConflictClaim + ConflictResolution classes (generic multi-way disputes)
- **Benefits:** Extensible (pressure, treaty, population-based claims), explainable
- **Value:** High (unifies conflict logic across sims)

### Priority 3: **ADVANCED FEATURES**

#### 6. `game/lifecycle` — Actor State Machines
- **Problem:** Labs 6–10 implement custom state transitions (created→active→eliminated)
- **Duplication:** Each lab manually checks conditions, updates state
- **Proposed:** ActorLifecycle + StateTransition classes (declarative state machines)
- **Benefits:** Reusable, auditable, extensible (supports emergence, vassalization, etc.)
- **Value:** Medium (enables advanced scenarios; not urgent)

## Pattern Evidence Across Labs

| Pattern | Labs | Lines/Lab | Total Duplication |
|---------|------|-----------|-------------------|
| Relation storage & queries | 6–10 (5 labs) | 30 | ~150 |
| Transport execution (plan + execute) | 4–10 (7 labs) | 200 | ~1400 |
| Event logging | 6–10 (5 labs) | 20 | ~100 |
| Conquest/conflict resolution | 3–10 (8 labs) | 150 | ~1200 |
| State transitions | 6–10 (5 labs) | 100 | ~500 |

**Total duplication addressable: ~3350 lines of code**

## Alignment with specs_EN.md

✅ All proposed layers align with core principles:
- A-6, A-15, A-19 (Resources, coexistence, multiplicity of spaces)
- A-21 (Heterogeneous metrics) — explicitly required by spec
- G-9, G-10 (Strategic gain/loss, path-dependent games)
- F-5, F-24 (LLM view, separation of responsibilities)

## Migration Strategy

1. **Implement Priority 1 layers** (3 classes × ~150 lines each)
2. **Pilot with Lab 8** (Relations Sim) to validate adoption pattern
3. **Incremental adoption:** Labs 6→9→10→4→5 (descending benefit/cost)
4. **Labs 1–3:** Lower priority (simpler; less benefit)

## Key Insight

These layers are NOT domain-specific. They address *structural patterns* that every lab needs:
- How to store and query relationships
- How to transfer resources with costs and disputes
- How to record and analyze events
- How to evaluate actors on multiple dimensions
- How to resolve conflicts fairly
- How to manage actor state transitions

**These belong in core because they're generic, reusable, and explicitly mentioned in specs_EN.md (A-21: heterogeneous metrics already required).**
