"""Graph generation utilities for the multi-agent simulation.

Responsibilities:
- Build a random undirected connected graph of N nodes
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


# --------------------------------------------------------------------------- #
# Random spanning-tree (Prüfer-free, random-walk based)                       #
# --------------------------------------------------------------------------- #


def _random_spanning_tree(node_ids: list[str], rng: random.Random) -> list[tuple[str, str]]:
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

    spice_flows = [rng.randint(config.min_spice_flow, config.max_spice_flow) for _ in range(n)]
    nodes = [
        RawNode(
            node_id=node_ids[i],
            spice_flow=spice_flows[i],
            x=positions[i][0],
            y=positions[i][1],
        )
        for i in range(n)
    ]

    sorted_edges = [(min(a, b), max(a, b)) for pair in edge_set for a, b in [sorted(pair)]]
    unique_edges: list[tuple[str, str]] = list({(a, b) for a, b in sorted_edges})
    unique_edges.sort()
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
    region_count = max(3, min(7, n // 5))
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
        desired_local = max(0, round((len(nodes) * (len(nodes) - 1) / 2) * config.graph_density * 0.35))
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

    # Inter-region sparse bridges to force chokepoints.
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
        if key not in edge_set:
            edge_set.add(key)
            degree[a] += 1
            degree[b] += 1
        gateways.add(a)
        gateways.add(b)

    # Optional very sparse extra region bridges.
    for _ in range(max(0, region_count // 3)):
        ra, rb = rng.sample(region_ids, 2)
        a = rng.choice(regions[ra])
        b = rng.choice(regions[rb])
        key = frozenset({a, b})
        if key not in edge_set and rng.random() < 0.4:
            edge_set.add(key)
            degree[a] += 1
            degree[b] += 1
            gateways.add(a)
            gateways.add(b)

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

    spice_flows = [rng.randint(config.min_spice_flow, config.max_spice_flow) for _ in range(n)]
    nodes = [
        RawNode(
            node_id=nid,
            spice_flow=spice_flows[i],
            x=pos_by_id[nid][0],
            y=pos_by_id[nid][1],
        )
        for i, nid in enumerate(node_ids)
    ]

    sorted_edges = [(min(a, b), max(a, b)) for pair in edge_set for a, b in [sorted(pair)]]
    unique_edges: list[tuple[str, str]] = list({(a, b) for a, b in sorted_edges})
    unique_edges.sort()
    return RawGraph(nodes=nodes, edges=unique_edges)


# --------------------------------------------------------------------------- #
# Public API                                                                   #
# --------------------------------------------------------------------------- #


def build_graph(config: SimConfig) -> RawGraph:
    """Build a random connected undirected graph according to *config*.

    Algorithm:
    1. Compute layout positions.
    2. Build a random spanning tree to guarantee connectivity.
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
