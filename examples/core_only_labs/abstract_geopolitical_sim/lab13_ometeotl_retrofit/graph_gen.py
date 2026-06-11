"""Graph generation utilities for the multi-agent simulation.

Responsibilities:
- Build random undirected graphs of N nodes (possibly disconnected in Lab 10)
- Assign per-node spice flow values via RNG
- Compute deterministic 2-D layout coordinates (ring or grid) for the web UI
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from .config import SimConfig

# --------------------------------------------------------------------------- #
# Data types                                                                   #
# --------------------------------------------------------------------------- #


@dataclass
class RawNode:
    """A node as produced by the graph generator, before simulation enrichment."""

    node_id: str
    spice_flow: int
    x: float  # normalised [0..1] for UI rendering
    y: float


@dataclass
class RawGraph:
    """Undirected graph produced by the generator."""

    nodes: list[RawNode] = field(default_factory=list)
    edges: list[tuple[str, str]] = field(default_factory=list)  # (node_id_a, node_id_b)

    def neighbors_of(self, node_id: str) -> list[str]:
        result: list[str] = []
        for a, b in self.edges:
            if a == node_id:
                result.append(b)
            elif b == node_id:
                result.append(a)
        return result

    def all_node_ids(self) -> list[str]:
        return [n.node_id for n in self.nodes]

    def node_by_id(self, node_id: str) -> RawNode:
        for n in self.nodes:
            if n.node_id == node_id:
                return n
        raise KeyError(node_id)


# --------------------------------------------------------------------------- #
# Layout helpers                                                               #
# --------------------------------------------------------------------------- #


def _ring_positions(n: int) -> list[tuple[float, float]]:
    """Place nodes evenly on a circle; coordinates in [0.05, 0.95]."""
    positions = []
    for i in range(n):
        angle = 2 * math.pi * i / n - math.pi / 2  # start at top
        x = 0.5 + 0.43 * math.cos(angle)
        y = 0.5 + 0.43 * math.sin(angle)
        positions.append((round(x, 4), round(y, 4)))
    return positions


def _grid_positions(n: int) -> list[tuple[float, float]]:
    """Place nodes in a near-square grid; coordinates in [0.05, 0.95]."""
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)
    positions = []
    for i in range(n):
        col = i % cols
        row = i // cols
        x = 0.05 + 0.90 * (col / max(cols - 1, 1))
        y = 0.05 + 0.90 * (row / max(rows - 1, 1))
        positions.append((round(x, 4), round(y, 4)))
    return positions


def _clamp01(v: float, low: float = 0.05, high: float = 0.95) -> float:
    return max(low, min(high, v))


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return math.sqrt(dx * dx + dy * dy)


def _apply_layout_readability(
    pos_by_id: dict[str, tuple[float, float]],
    edges: list[tuple[str, str]],
    rng: random.Random,
    min_dist: float,
    iterations: int = 80,
) -> dict[str, tuple[float, float]]:
    """Improve readability with simple force rules.

    Rules:
    - Repel nodes that are too close (reduce node overlap).
    - Keep adjacent nodes loosely connected (avoid excessive drift).
    - Add tiny random motion so the result stays organic, not perfectly rigid.
    """
    ids = list(pos_by_id.keys())
    pos = {nid: [pos_by_id[nid][0], pos_by_id[nid][1]] for nid in ids}

    # Mild target length proportional to density target; keeps links legible.
    # Slightly larger upper bound increases average node separation.
    target_len = max(0.12, min(0.24, min_dist * 1.75))

    for _ in range(iterations):
        forces: dict[str, list[float]] = {nid: [0.0, 0.0] for nid in ids}

        # Pairwise repulsion for close nodes.
        for i in range(len(ids)):
            a = ids[i]
            ax, ay = pos[a]
            for j in range(i + 1, len(ids)):
                b = ids[j]
                bx, by = pos[b]
                dx = ax - bx
                dy = ay - by
                d2 = dx * dx + dy * dy
                if d2 <= 1e-8:
                    # Break exact overlap deterministically.
                    dx = rng.uniform(-0.001, 0.001)
                    dy = rng.uniform(-0.001, 0.001)
                    d2 = dx * dx + dy * dy
                d = math.sqrt(d2)
                if d < min_dist:
                    # Stronger as nodes get closer.
                    push = (min_dist - d) * 0.060
                    ux = dx / d
                    uy = dy / d
                    fx = ux * push
                    fy = uy * push
                    forces[a][0] += fx
                    forces[a][1] += fy
                    forces[b][0] -= fx
                    forces[b][1] -= fy

        # Spring-like attraction on edges to avoid over-separation.
        for a, b in edges:
            ax, ay = pos[a]
            bx, by = pos[b]
            dx = bx - ax
            dy = by - ay
            d2 = dx * dx + dy * dy
            if d2 <= 1e-8:
                continue
            d = math.sqrt(d2)
            delta = d - target_len
            pull = delta * 0.008
            ux = dx / d
            uy = dy / d
            fx = ux * pull
            fy = uy * pull
            forces[a][0] += fx
            forces[a][1] += fy
            forces[b][0] -= fx
            forces[b][1] -= fy

        # Integrate forces with tiny jitter for organic look.
        for nid in ids:
            jx = rng.uniform(-0.0008, 0.0008)
            jy = rng.uniform(-0.0008, 0.0008)
            pos[nid][0] = _clamp01(pos[nid][0] + forces[nid][0] + jx)
            pos[nid][1] = _clamp01(pos[nid][1] + forces[nid][1] + jy)

    return {nid: (round(pos[nid][0], 4), round(pos[nid][1], 4)) for nid in ids}


# --------------------------------------------------------------------------- #
# Random spanning-tree (Prüfer-free, random-walk based)                       #
# --------------------------------------------------------------------------- #


def _random_spanning_tree(
    node_ids: list[str], rng: random.Random
) -> list[tuple[str, str]]:
    """Return a set of edges forming a random spanning tree (random insertion order)."""
    shuffled = node_ids[:]
    rng.shuffle(shuffled)
    in_tree = {shuffled[0]}
    edges: list[tuple[str, str]] = []
    remaining = shuffled[1:]
    rng.shuffle(remaining)
    for node in remaining:
        target = rng.choice(list(in_tree))
        edges.append((node, target))
        in_tree.add(node)
    return edges


def _build_uniform_graph(
    node_ids: list[str],
    positions: list[tuple[float, float]],
    rng: random.Random,
    config: SimConfig,
) -> RawGraph:
    """Current generic random graph style (baseline mode)."""
    n = len(node_ids)

    edge_set: set[frozenset[str]] = set()
    for a, b in _random_spanning_tree(node_ids, rng):
        edge_set.add(frozenset({a, b}))

    max_extra_edges = n * (n - 1) // 2 - (n - 1)
    target_extra = round(config.graph_density * max_extra_edges)
    attempts = 0
    added = 0
    while added < target_extra and attempts < max_extra_edges * 4:
        a, b = rng.sample(node_ids, 2)
        key = frozenset({a, b})
        if key not in edge_set:
            edge_set.add(key)
            added += 1
        attempts += 1

    edge_list = [(min(a, b), max(a, b)) for pair in edge_set for a, b in [sorted(pair)]]
    unique_edges: list[tuple[str, str]] = list({(a, b) for a, b in edge_list})
    unique_edges.sort()

    # Readability pass: reduce node overlap and keep links legible.
    pos_by_id = {node_ids[i]: positions[i] for i in range(n)}
    pos_by_id = _apply_layout_readability(
        pos_by_id=pos_by_id,
        edges=unique_edges,
        rng=rng,
        min_dist=config.layout_min_node_distance,
        iterations=110,
    )

    spice_flows = [
        rng.randint(config.min_spice_flow, config.max_spice_flow) for _ in range(n)
    ]
    nodes = [
        RawNode(
            node_id=node_ids[i],
            spice_flow=spice_flows[i],
            x=pos_by_id[node_ids[i]][0],
            y=pos_by_id[node_ids[i]][1],
        )
        for i in range(n)
    ]

    return RawGraph(nodes=nodes, edges=unique_edges)


def _assign_nodes_to_regions(
    node_ids: list[str],
    region_count: int,
    rng: random.Random,
) -> tuple[list[tuple[float, float]], dict[int, list[str]]]:
    """Create region centers and assign nodes to regions with balanced sizes."""
    centers: list[tuple[float, float]] = []
    for _ in range(region_count):
        # Keep centers away from borders to leave room for cluster spread.
        centers.append((rng.uniform(0.15, 0.85), rng.uniform(0.15, 0.85)))

    shuffled = node_ids[:]
    rng.shuffle(shuffled)
    regions: dict[int, list[str]] = {i: [] for i in range(region_count)}

    # Seed each region with at least one node.
    for i, nid in enumerate(shuffled[:region_count]):
        regions[i].append(nid)

    # Balanced fill of remaining nodes.
    for nid in shuffled[region_count:]:
        smallest = min(regions, key=lambda r: len(regions[r]))
        regions[smallest].append(nid)

    return centers, regions


def _region_count_for_preset(n: int, preset: str) -> int:
    """Return number of geographic regions based on topology preset."""
    if preset == "pangea":
        # One dominant landmass.
        return 1
    if preset == "archipelago":
        # Many small landmasses.
        return max(5, min(12, n // 3))
    # Default: continents
    return max(3, min(7, n // 5))


def _intra_region_tree(
    region_nodes: list[str],
    pos_by_id: dict[str, tuple[float, float]],
    rng: random.Random,
) -> list[tuple[str, str]]:
    """Randomized Prim-like tree favoring shorter local edges."""
    if len(region_nodes) <= 1:
        return []

    start = rng.choice(region_nodes)
    in_tree = {start}
    remaining = set(region_nodes) - {start}
    edges: list[tuple[str, str]] = []

    while remaining:
        candidates: list[tuple[float, str, str]] = []
        for a in in_tree:
            for b in remaining:
                d = _distance(pos_by_id[a], pos_by_id[b])
                # Small random jitter keeps geometry but avoids deterministic sameness.
                candidates.append((d + rng.random() * 0.02, a, b))
        candidates.sort(key=lambda x: x[0])
        _, a_best, b_best = candidates[0]
        edges.append((a_best, b_best))
        in_tree.add(b_best)
        remaining.remove(b_best)

    return edges


def _degree_map_from_edges(
    node_ids: list[str],
    edge_set: set[frozenset[str]],
) -> dict[str, int]:
    degree = {nid: 0 for nid in node_ids}
    for pair in edge_set:
        a, b = tuple(pair)
        degree[a] += 1
        degree[b] += 1
    return degree


def _is_connected_with_edges(
    node_ids: list[str],
    edge_set: set[frozenset[str]],
) -> bool:
    if not node_ids:
        return True
    adj: dict[str, list[str]] = {nid: [] for nid in node_ids}
    for pair in edge_set:
        a, b = tuple(pair)
        adj[a].append(b)
        adj[b].append(a)
    seen = {node_ids[0]}
    queue = [node_ids[0]]
    head = 0
    while head < len(queue):
        cur = queue[head]
        head += 1
        for nb in adj[cur]:
            if nb not in seen:
                seen.add(nb)
                queue.append(nb)
    return len(seen) == len(node_ids)


def _enforce_dead_ends(
    node_ids: list[str],
    edge_set: set[frozenset[str]],
    leaf_candidates: list[str],
    target_leaf_count: int,
    rng: random.Random,
) -> None:
    """Try to guarantee a minimum number of leaf nodes while preserving connectivity."""
    target_leaf_count = max(1, target_leaf_count)

    def neighbors_of(nid: str) -> list[str]:
        out: list[str] = []
        for pair in edge_set:
            if nid in pair:
                a, b = tuple(pair)
                out.append(b if a == nid else a)
        return out

    # Phase 1: prune candidate incident edges (when safe) until enough leaves.
    shuffled = leaf_candidates[:]
    rng.shuffle(shuffled)
    for leaf in shuffled:
        degree = _degree_map_from_edges(node_ids, edge_set)
        leaf_count = sum(1 for d in degree.values() if d == 1)
        if leaf_count >= target_leaf_count:
            break
        if degree.get(leaf, 0) <= 1:
            continue

        incident = []
        for pair in edge_set:
            if leaf in pair:
                a, b = tuple(pair)
                other = b if a == leaf else a
                incident.append((other, pair))
        # Keep the closest anchor edge, try to drop other incident edges.
        if not incident:
            continue
        keep_neighbor = incident[0][0]
        removable = [pair for other, pair in incident if other != keep_neighbor]
        for pair in removable:
            if degree.get(leaf, 0) <= 1:
                break
            edge_set.remove(pair)
            if not _is_connected_with_edges(node_ids, edge_set):
                edge_set.add(pair)
            degree = _degree_map_from_edges(node_ids, edge_set)

    # Phase 2: if still short, force one-corridor attachment for best candidates.
    degree = _degree_map_from_edges(node_ids, edge_set)
    leaf_count = sum(1 for d in degree.values() if d == 1)
    if leaf_count >= target_leaf_count:
        return

    for leaf in shuffled:
        degree = _degree_map_from_edges(node_ids, edge_set)
        leaf_count = sum(1 for d in degree.values() if d == 1)
        if leaf_count >= target_leaf_count:
            break
        if degree.get(leaf, 0) == 1:
            continue

        nbs = neighbors_of(leaf)
        if not nbs:
            continue
        keep = nbs[0]
        for other in nbs:
            if other == keep:
                continue
            pair = frozenset({leaf, other})
            if pair in edge_set:
                edge_set.remove(pair)
                if not _is_connected_with_edges(node_ids, edge_set):
                    edge_set.add(pair)


def _build_geographic_graph(
    node_ids: list[str],
    rng: random.Random,
    config: SimConfig,
) -> RawGraph:
    """Generate a map-like graph with regions, bridges, and cul-de-sacs.

    Design:
    - Regions produce wide intra-connected areas
    - Limited inter-region bridges create chokepoints
    - Some nodes are intentionally kept leaf-like to create dead ends
    """
    n = len(node_ids)
    preset = config.geography_preset
    region_count = min(n, _region_count_for_preset(n, preset))
    region_centers, regions = _assign_nodes_to_regions(node_ids, region_count, rng)

    pos_by_id: dict[str, tuple[float, float]] = {}
    for ridx, nodes in regions.items():
        cx, cy = region_centers[ridx]
        spread = 0.06 + 0.03 * min(4, len(nodes))
        for nid in nodes:
            px = _clamp01(rng.gauss(cx, spread))
            py = _clamp01(rng.gauss(cy, spread))
            pos_by_id[nid] = (round(px, 4), round(py, 4))

    # Base intra-region trees for connectivity.
    edge_set: set[frozenset[str]] = set()
    degree: dict[str, int] = {nid: 0 for nid in node_ids}
    for nodes in regions.values():
        for a, b in _intra_region_tree(nodes, pos_by_id, rng):
            key = frozenset({a, b})
            if key in edge_set:
                continue
            edge_set.add(key)
            degree[a] += 1
            degree[b] += 1

    # Choose nodes that should remain likely dead ends.
    leaf_budget = max(1, n // 8)
    leaf_candidates = set(rng.sample(node_ids, k=min(leaf_budget, len(node_ids))))

    # Add local edges to make broader sections (avoid leaf candidates).
    for nodes in regions.values():
        if len(nodes) < 3:
            continue
        if preset == "pangea":
            local_factor = 0.42
        elif preset == "archipelago":
            local_factor = 0.25
        else:
            local_factor = 0.32
        desired_local = max(
            0,
            round(
                (len(nodes) * (len(nodes) - 1) / 2)
                * config.graph_density
                * local_factor
            ),
        )
        attempts = 0
        added = 0
        while added < desired_local and attempts < len(nodes) * len(nodes) * 2:
            a, b = rng.sample(nodes, 2)
            attempts += 1
            if a in leaf_candidates or b in leaf_candidates:
                continue
            key = frozenset({a, b})
            if key in edge_set:
                continue
            # Favor geographically short local edges.
            if _distance(pos_by_id[a], pos_by_id[b]) > 0.22 and rng.random() < 0.7:
                continue
            edge_set.add(key)
            degree[a] += 1
            degree[b] += 1
            added += 1

    # Inter-region sparse bridges. In Lab 10, these may be absent, allowing
    # disconnected regions at start.
    region_ids = list(regions.keys())
    rng.shuffle(region_ids)
    gateways: set[str] = set()
    for i in range(len(region_ids) - 1):
        ra = region_ids[i]
        rb = region_ids[i + 1]

        # Find closest cross-region node pair as bridge endpoints.
        best_pair: tuple[str, str] | None = None
        best_d = 999.0
        for a in regions[ra]:
            for b in regions[rb]:
                d = _distance(pos_by_id[a], pos_by_id[b])
                if d < best_d:
                    best_d = d
                    best_pair = (a, b)

        if best_pair is None:
            continue
        a, b = best_pair
        key = frozenset({a, b})
        if config.allow_disconnected_regions:
            if preset == "pangea":
                p_bridge = 1.0
            elif preset == "archipelago":
                p_bridge = 0.25
            else:
                p_bridge = 0.35
            should_add = rng.random() < p_bridge
        else:
            should_add = True

        if should_add and key not in edge_set:
            edge_set.add(key)
            degree[a] += 1
            degree[b] += 1
            gateways.add(a)
            gateways.add(b)

    # Optional very sparse extra region bridges (kept minimal to preserve bottlenecks).
    if preset == "pangea":
        extra_bridge_budget = 0
    elif preset == "archipelago":
        # Many islands may need occasional extra lanes.
        extra_bridge_budget = 1 if region_count >= 7 else 0
    else:
        # Continents: keep few corridors.
        extra_bridge_budget = (
            1 if config.graph_density > 0.58 and region_count >= 5 else 0
        )
    for _ in range(extra_bridge_budget):
        ra, rb = rng.sample(region_ids, 2)
        a = rng.choice(regions[ra])
        b = rng.choice(regions[rb])
        key = frozenset({a, b})
        if preset == "archipelago":
            p_extra_bridge = 0.30
        else:
            p_extra_bridge = 0.16
        if key not in edge_set and rng.random() < p_extra_bridge:
            edge_set.add(key)
            degree[a] += 1
            degree[b] += 1
            gateways.add(a)
            gateways.add(b)

    # Enforce a visible number of dead ends without disconnecting the graph.
    _enforce_dead_ends(
        node_ids=node_ids,
        edge_set=edge_set,
        leaf_candidates=list(leaf_candidates),
        target_leaf_count=max(1, n // 10 if preset != "pangea" else n // 8),
        rng=rng,
    )

    degree = _degree_map_from_edges(node_ids, edge_set)

    # Ensure at least one true dead-end if none naturally occurred.
    if all(v > 1 for v in degree.values()):
        # Attach one leaf candidate to a nearby non-leaf node.
        leaf = next(iter(leaf_candidates)) if leaf_candidates else node_ids[0]
        anchor = min(
            (nid for nid in node_ids if nid != leaf),
            key=lambda nid: _distance(pos_by_id[leaf], pos_by_id[nid]),
        )
        # Remove all leaf edges then force one.
        to_remove = [pair for pair in edge_set if leaf in pair]
        for pair in to_remove:
            a, b = tuple(pair)
            edge_set.remove(pair)
            degree[a] = max(0, degree[a] - 1)
            degree[b] = max(0, degree[b] - 1)
        forced = frozenset({leaf, anchor})
        if forced not in edge_set:
            edge_set.add(forced)
            degree[leaf] += 1
            degree[anchor] += 1

    sorted_edges = [
        (min(a, b), max(a, b)) for pair in edge_set for a, b in [sorted(pair)]
    ]
    unique_edges: list[tuple[str, str]] = list({(a, b) for a, b in sorted_edges})
    unique_edges.sort()

    # Readability pass: keep clusters but reduce near-overlaps.
    geo_min_dist = max(0.06, config.layout_min_node_distance * 0.77)
    pos_by_id = _apply_layout_readability(
        pos_by_id=pos_by_id,
        edges=unique_edges,
        rng=rng,
        min_dist=geo_min_dist,
        iterations=90,
    )

    spice_flows = [
        rng.randint(config.min_spice_flow, config.max_spice_flow) for _ in range(n)
    ]
    nodes = [
        RawNode(
            node_id=nid,
            spice_flow=spice_flows[i],
            x=pos_by_id[nid][0],
            y=pos_by_id[nid][1],
        )
        for i, nid in enumerate(node_ids)
    ]

    return RawGraph(nodes=nodes, edges=unique_edges)


# --------------------------------------------------------------------------- #
# Public API                                                                   #
# --------------------------------------------------------------------------- #


def build_graph(config: SimConfig) -> RawGraph:
    """Build a random undirected graph according to *config*.

    Algorithm:
    1. Compute layout positions.
    2. Build a baseline edge structure (connected in uniform mode).
    3. Add random extra edges until the target density is reached.
    4. Assign spice flows via RNG.
    """
    config.validate()

    seed = config.seed if config.seed is not None else random.randint(0, 2**32 - 1)
    rng = random.Random(seed)

    n = config.num_nodes
    node_ids = [f"node-{i}" for i in range(n)]

    if config.graph_mode == "geographic":
        return _build_geographic_graph(node_ids=node_ids, rng=rng, config=config)

    # Baseline mode keeps explicit layout choice.
    if config.layout == "grid":
        positions = _grid_positions(n)
    else:
        positions = _ring_positions(n)
    return _build_uniform_graph(
        node_ids=node_ids,
        positions=positions,
        rng=rng,
        config=config,
    )


def bfs_distances(graph: RawGraph, source: str) -> dict[str, int]:
    """Return BFS distances from *source* to every other node (unreachable → -1)."""
    dist: dict[str, int] = {source: 0}
    queue = [source]
    head = 0
    while head < len(queue):
        current = queue[head]
        head += 1
        for nb in graph.neighbors_of(current):
            if nb not in dist:
                dist[nb] = dist[current] + 1
                queue.append(nb)
    for node_id in graph.all_node_ids():
        if node_id not in dist:
            dist[node_id] = -1
    return dist
