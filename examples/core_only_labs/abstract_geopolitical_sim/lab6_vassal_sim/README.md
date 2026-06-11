# Lab 6: Vassal Hierarchy Simulation

Lab 6 extends [Lab 5](../lab5_behavior_sim/) with hierarchical faction dynamics:

- autonomous vassal split when local drift is high,
- independent secession only when drift against the top ancestor is high,
- multi-order vassal chains,
- allied logistics behavior within one hierarchy,
- tribute from vassal capitals to direct parent capitals.

Behavior, logistics, and map generation from Lab 5 are preserved.

## Vassal Dynamics

Drift checks now use two thresholds:

- `drift_threshold_fraction`: autonomy threshold versus direct parent genome.
- `top_secession_threshold_fraction`: full secession threshold versus top ancestor genome.

When a node crosses autonomy threshold:

- if top-ancestor drift is still below secession threshold, it becomes a new vassal;
- otherwise it secedes as a new independent root faction.

Vassals:

- plan and act autonomously,
- do not share perception,
- are non-hostile with same-top factions,
- transfer `vassal_tribute_fraction` of their capital stock each tick to their parent.

## Hierarchy Metadata

Serialized faction payload now includes:

- `parent_faction_id`
- `top_ancestor_id`
- `hierarchy_depth`
- `is_vassal`

Faction IDs for vassals follow lineage naming:

- root: `faction-0`
- first child: `faction-0.v1`
- grand-child: `faction-0.v1.v1`

## Running Lab 6

```bash
cd /path/to/ometeotl
python -m examples.lab6_vassal_sim.web_server
```

Server URL: `http://127.0.0.1:8770/`

## Running Tests

```bash
python -m pytest examples/lab6_vassal_sim/test_sim_local.py -v
```
