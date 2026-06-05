/**
 * app.js — Lab 14 Client-Side Calculations Simulation client
 *
 * Responsibilities:
 *  - Fetch /api/state (minimal raw state) and compute all derived display values
 *    locally before rendering — keeping the server a thin state store.
 *  - Render SVG graph (nodes, edges, ownership colours)
 *  - Step (manual) and auto-run with configurable speed
 *  - Faction legend sidebar: total spice, income, ECLOZ, tech levels
 *  - Config form submission → POST /api/reset
 *  - Pressure ring arcs on nodes to show conquest progress
 *  - Devastation ring arcs on nodes to show devastation level
 *  - Node label shows spice_stock held at that node
 *  - Edge thickness reflects link max_flow capacity
 *  - Technology panel: per-faction Diplo / Cohé / Logi progress bars + α vector
 *  - Auto-untangle: force-directed layout with edge-crossing resolution
 *
 * Client-side derivations (computeDerivedState):
 *  Per node : color, effective_stock_cap, effective_production, flip_count_in_window
 *  Per faction: node_count, total_spice, spice_income, perceived_relations
 */

"use strict";

const API = "http://127.0.0.1:8777";  // Lab 14 server port

// SVG viewport dimensions (must match viewBox in HTML)
const SVG_W = 800;
const SVG_H = 600;
const NODE_R = 22;
const NODE_R_CAPITAL = 27;

// ─────────────────────────────────────────────────────────── //
// DOM refs                                                    //
// ─────────────────────────────────────────────────────────── //

const svgEl        = document.getElementById("graph-svg");
const edgesLayer   = document.getElementById("edges-layer");
const nodesLayer   = document.getElementById("nodes-layer");
const labelsLayer  = document.getElementById("labels-layer");
const tickCounter  = document.getElementById("tick-counter");
const statusText   = document.getElementById("status-text");
const eventList    = document.getElementById("event-list");
const factionList  = document.getElementById("faction-list");
const relationsMeta = document.getElementById("relations-meta");
const relationsList = document.getElementById("relations-list");
const symbolicMeta = document.getElementById("symbolic-meta");
const symbolicList = document.getElementById("symbolic-list");
const techMeta     = document.getElementById("tech-meta");
const techList     = document.getElementById("tech-list");
const speedSlider  = document.getElementById("speed-slider");
const speedLabel   = document.getElementById("speed-label");
const btnStepBack  = document.getElementById("btn-step-back");
const btnStep      = document.getElementById("btn-step");
const btnReverseRun = document.getElementById("btn-reverse-run");
const btnAutorun   = document.getElementById("btn-autorun");
const btnReset     = document.getElementById("btn-reset");
const configForm   = document.getElementById("config-form");

// ─────────────────────────────────────────────────────────── //
// State                                                       //
// ─────────────────────────────────────────────────────────── //

let autorunTimer   = null;
let reverseTimer   = null;
let lastState      = null;
let factionColors  = {};  // faction_id → hex colour (cached for edge colouring)

// ── Client-side layout overrides (force layout + user drag) ── //
const nodeOverrides = {};     // node_id → {x, y} normalized [0..1]
const pinnedNodes   = new Set(); // user-dragged nodes (excluded from force layout)
let selectedNodeId  = null;
let lastTopologyKey = "";

// ── Drag state ──────────────────────────────────────────────── //
let dragState  = null; // {nodeId, startSvgX, startSvgY, startNX, startNY}
let dragMoved  = false;

// ─────────────────────────────────────────────────────────── //
// Utility                                                     //
// ─────────────────────────────────────────────────────────── //

function svgNS(tag, attrs = {}) {
  const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  return el;
}

function nodePos(node) {
  const ov = nodeOverrides[node.node_id];
  if (ov) return { cx: Math.round(ov.x * SVG_W), cy: Math.round(ov.y * SVG_H) };
  return { cx: Math.round(node.x * SVG_W), cy: Math.round(node.y * SVG_H) };
}

function describeArc(cx, cy, r, startAngle, endAngle) {
  // Returns an SVG arc path string; angles in radians
  const x1 = cx + r * Math.cos(startAngle);
  const y1 = cy + r * Math.sin(startAngle);
  const x2 = cx + r * Math.cos(endAngle);
  const y2 = cy + r * Math.sin(endAngle);
  const largeArc = endAngle - startAngle > Math.PI ? 1 : 0;
  return `M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2}`;
}

function edgeSeed(a, b) {
  // Small deterministic hash used to keep edge bend stable across frames.
  const s = `${a}|${b}`;
  let h = 2166136261;
  for (let i = 0; i < s.length; i += 1) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return (h >>> 0);
}

// ── Topology fingerprint ───────────────────────────────────── //
function topologyKey(nodes, edges) {
  const nids = nodes.map(n => n.node_id).sort().join(",");
  const eids = edges.map(e => [e.a, e.b].sort().join("-")).sort().join("|");
  return `${nids};${eids}`;
}

// ── Segment intersection test (strict: excludes shared endpoints) //
function segmentsIntersect(p1, p2, p3, p4) {
  const d1x = p2.x - p1.x, d1y = p2.y - p1.y;
  const d2x = p4.x - p3.x, d2y = p4.y - p3.y;
  const denom = d1x * d2y - d1y * d2x;
  if (Math.abs(denom) < 1e-10) return false;
  const t = ((p3.x - p1.x) * d2y - (p3.y - p1.y) * d2x) / denom;
  const u = ((p3.x - p1.x) * d1y - (p3.y - p1.y) * d1x) / denom;
  return t > 0.02 && t < 0.98 && u > 0.02 && u < 0.98;
}

// ── Client-side force-directed layout ─────────────────────── //
function runForceLayout(nodes, edges) {
  if (nodes.length < 2) return;

  // Work in pixel space matching the SVG viewBox
  const pos = {};
  for (const n of nodes) {
    const ov = nodeOverrides[n.node_id];
    pos[n.node_id] = ov
      ? { x: ov.x * SVG_W, y: ov.y * SVG_H }
      : { x: n.x * SVG_W, y: n.y * SVG_H };
  }

  const ids = nodes.map(n => n.node_id);
  const k = Math.sqrt((SVG_W * SVG_H) / nodes.length) * 0.85;
  const MARGIN = 44;
  const ITERS  = 220;

  for (let iter = 0; iter < ITERS; iter++) {
    const cool = Math.pow(1 - iter / ITERS, 1.4);
    const maxStep = Math.max(1, 55 * cool);
    const fx = {}, fy = {};
    for (const id of ids) { fx[id] = 0; fy[id] = 0; }

    // Repulsion between every pair
    for (let i = 0; i < ids.length; i++) {
      for (let j = i + 1; j < ids.length; j++) {
        const a = ids[i], b = ids[j];
        const dx = pos[b].x - pos[a].x;
        const dy = pos[b].y - pos[a].y;
        const dist = Math.hypot(dx, dy) || 1;
        const f = (k * k) / dist;
        const ux = (dx / dist) * f;
        const uy = (dy / dist) * f;
        fx[b] += ux; fy[b] += uy;
        fx[a] -= ux; fy[a] -= uy;
      }
    }

    // Spring attraction along edges (target distance k)
    for (const e of edges) {
      if (!pos[e.a] || !pos[e.b]) continue;
      const dx = pos[e.b].x - pos[e.a].x;
      const dy = pos[e.b].y - pos[e.a].y;
      const dist = Math.hypot(dx, dy) || 1;
      const f = (dist - k) / dist;
      fx[e.b] -= dx * f; fy[e.b] -= dy * f;
      fx[e.a] += dx * f; fy[e.a] += dy * f;
    }

    // Node-edge clearance: bidirectional — repel node from edge AND edge endpoints from node
    const nodeR_rl = nodes.length >= 30 ? 14 : nodes.length >= 22 ? 17 : NODE_R;
    const clearRL  = nodeR_rl * 3.5;
    for (const node of nodes) {
      const np = pos[node.node_id];
      if (!np) continue;
      for (const edge of edges) {
        if (edge.a === node.node_id || edge.b === node.node_id) continue;
        const ap = pos[edge.a], bp = pos[edge.b];
        if (!ap || !bp) continue;
        const edx = bp.x - ap.x, edy = bp.y - ap.y;
        const edLen2 = edx * edx + edy * edy;
        if (edLen2 < 1) continue;
        const t = Math.max(0.05, Math.min(0.95,
          ((np.x - ap.x) * edx + (np.y - ap.y) * edy) / edLen2));
        const cx = ap.x + t * edx, cy = ap.y + t * edy;
        const d  = Math.hypot(np.x - cx, np.y - cy) || 0.5;
        if (d < clearRL) {
          const px = np.x - cx, py = np.y - cy;
          const f  = (clearRL - d) / d * 2.0;
          fx[node.node_id] += px * f; fy[node.node_id] += py * f;
          if (!pinnedNodes.has(edge.a)) { fx[edge.a] -= px * f * (1 - t) * 0.5; fy[edge.a] -= py * f * (1 - t) * 0.5; }
          if (!pinnedNodes.has(edge.b)) { fx[edge.b] -= px * f * t       * 0.5; fy[edge.b] -= py * f * t       * 0.5; }
        }
      }
    }

    // Edge-edge crossing force: strong push to resolve actual crossings
    for (let i = 0; i < edges.length; i++) {
      for (let j = i + 1; j < edges.length; j++) {
        const e1 = edges[i], e2 = edges[j];
        if (e1.a === e2.a || e1.a === e2.b || e1.b === e2.a || e1.b === e2.b) continue;
        const p1 = pos[e1.a], p2 = pos[e1.b], p3 = pos[e2.a], p4 = pos[e2.b];
        if (!p1 || !p2 || !p3 || !p4) continue;
        if (!segmentsIntersect(p1, p2, p3, p4)) continue;
        const m1x = (p1.x + p2.x) / 2, m1y = (p1.y + p2.y) / 2;
        const m2x = (p3.x + p4.x) / 2, m2y = (p3.y + p4.y) / 2;
        const dx = m2x - m1x, dy = m2y - m1y;
        const dist = Math.hypot(dx, dy) || 0.5;
        const f  = 2.5 * k * k / dist;
        const ux = (dx / dist) * f * 0.5, uy = (dy / dist) * f * 0.5;
        if (!pinnedNodes.has(e1.a)) { fx[e1.a] -= ux; fy[e1.a] -= uy; }
        if (!pinnedNodes.has(e1.b)) { fx[e1.b] -= ux; fy[e1.b] -= uy; }
        if (!pinnedNodes.has(e2.a)) { fx[e2.a] += ux; fy[e2.a] += uy; }
        if (!pinnedNodes.has(e2.b)) { fx[e2.b] += ux; fy[e2.b] += uy; }
      }
    }

    // Gravity toward canvas center — prevents nodes clustering at periphery
    const gx = SVG_W / 2, gy = SVG_H / 2;
    const GRAVITY = 3.50;
    for (const id of ids) {
      fx[id] += GRAVITY * (gx - pos[id].x);
      fy[id] += GRAVITY * (gy - pos[id].y);
    }

    // Apply with cooling + boundary clamping
    for (const id of ids) {
      if (pinnedNodes.has(id)) continue;
      const mag = Math.hypot(fx[id], fy[id]) || 1e-6;
      const step = Math.min(maxStep, mag) / mag;
      pos[id].x = Math.max(MARGIN, Math.min(SVG_W - MARGIN, pos[id].x + fx[id] * step));
      pos[id].y = Math.max(MARGIN, Math.min(SVG_H - MARGIN, pos[id].y + fy[id] * step));
    }
  }

  // Persist results as layout overrides
  for (const n of nodes) {
    if (!pinnedNodes.has(n.node_id)) {
      nodeOverrides[n.node_id] = { x: pos[n.node_id].x / SVG_W, y: pos[n.node_id].y / SVG_H };
    }
  }
}

// ── SVG cursor → viewBox coordinate conversion ────────────── //
function svgPoint(e) {
  const rect = svgEl.getBoundingClientRect();
  return {
    x: (e.clientX - rect.left) * (SVG_W / rect.width),
    y: (e.clientY - rect.top)  * (SVG_H / rect.height),
  };
}

// ── Convert viewBox coords to panel-relative screen coords ─── //
function svgViewboxToPanel(vbX, vbY) {
  const svgRect   = svgEl.getBoundingClientRect();
  const panelRect = document.getElementById("map-panel").getBoundingClientRect();
  return {
    x: svgRect.left + vbX * (svgRect.width  / SVG_W) - panelRect.left,
    y: svgRect.top  + vbY * (svgRect.height / SVG_H) - panelRect.top,
  };
}

function describeOrganicEdge(pa, pb, bendSign, bendMagPx) {
  const dx = pb.cx - pa.cx;
  const dy = pb.cy - pa.cy;
  const len = Math.hypot(dx, dy);
  if (len < 1e-6 || bendMagPx <= 0) {
    return `M ${pa.cx} ${pa.cy} L ${pb.cx} ${pb.cy}`;
  }
  // Perpendicular offset around midpoint.
  const nx = -dy / len;
  const ny = dx / len;
  const mx = (pa.cx + pb.cx) / 2;
  const my = (pa.cy + pb.cy) / 2;
  const cx = mx + bendSign * nx * bendMagPx;
  const cy = my + bendSign * ny * bendMagPx;
  return `M ${pa.cx} ${pa.cy} Q ${cx} ${cy} ${pb.cx} ${pb.cy}`;
}

function capacityColor(value, minValue, maxValue) {
  // 0 -> red, 1 -> blue (with slight purple midpoint for readability)
  const range = Math.max(1e-9, maxValue - minValue);
  const t = Math.max(0, Math.min(1, (value - minValue) / range));
  const r = Math.round(220 * (1 - t) + 70 * t);
  const g = Math.round(70 * (1 - t) + 120 * t);
  const b = Math.round(70 * (1 - t) + 230 * t);
  return `rgb(${r}, ${g}, ${b})`;
}

function activeFactionIds(state) {
  return new Set(
    Object.values(state.factions || {})
      .filter(f => !f.is_eliminated && (f.node_count ?? 0) > 0)
      .map(f => f.faction_id)
  );
}

function averageRelationForFaction(state, factionId) {
  const activeIds = activeFactionIds(state);
  if (!activeIds.has(factionId)) return null;

  const relations = (Array.isArray(state.relations) ? state.relations : [])
    .filter(r => activeIds.has(r.a) && activeIds.has(r.b));
  const values = relations
    .filter(r => r.a === factionId || r.b === factionId)
    .map(r => (typeof r.value === "number" ? r.value : 0));
  if (!values.length) return null;
  const mean = values.reduce((acc, v) => acc + v, 0) / values.length;
  return mean;
}

function relationSummary(state) {
  const activeIds = activeFactionIds(state);
  const relations = (Array.isArray(state.relations) ? state.relations : [])
    .filter(r => activeIds.has(r.a) && activeIds.has(r.b));
  if (!relations.length) return "no known relations";
  const mean = relations.reduce((acc, r) => {
    const v = typeof r.value === "number" ? r.value : 0;
    return acc + v;
  }, 0) / relations.length;
  return `${relations.length} known pair${relations.length !== 1 ? "s" : ""}, avg R ${mean.toFixed(2)}`;
}

// ─────────────────────────────────────────────────────────── //
// Client-side derivations                                     //
// ─────────────────────────────────────────────────────────── //

/**
 * Enrich a raw server payload with all derived display fields so the rest of
 * the render pipeline can read them without knowing they were computed here.
 *
 * The server (Lab 14) intentionally omits:
 *   node  : color, effective_stock_cap, effective_production, flip_count_in_window
 *   faction: node_count, total_spice, spice_income, perceived_relations
 *
 * This function mutates `raw` in-place and returns it.
 */
function computeDerivedState(raw) {
  const cfg     = raw.config;
  const tick    = raw.tick;
  const factions = raw.factions; // { faction_id: faction }

  // Build O(1) relation lookup keyed by sorted pair
  const relMap = {};
  for (const r of (raw.relations || [])) {
    const key = r.a < r.b ? `${r.a}\x00${r.b}` : `${r.b}\x00${r.a}`;
    relMap[key] = r.value;
  }

  function relationBetween(a, b) {
    if (a === b) return 1.0;
    const key = a < b ? `${a}\x00${b}` : `${b}\x00${a}`;
    const v = relMap[key];
    return v === undefined ? null : v;
  }

  // Per-faction accumulators
  const fNodeCount    = {};
  const fTotalSpice   = {};
  const fSpiceIncome  = {};
  for (const fid of Object.keys(factions)) {
    fNodeCount[fid]   = 0;
    fTotalSpice[fid]  = 0;
    fSpiceIncome[fid] = 0;
  }

  // Derive per-node fields and accumulate faction totals in one pass
  for (const node of raw.nodes) {
    const ownerId = node.owner_id;
    const faction = ownerId ? factions[ownerId] : null;

    // color
    node.color = faction ? faction.color : "#cccccc";

    // effective_stock_cap
    const logiCap = faction
      ? cfg.base_stock_cap + faction.tech.logi * cfg.logi_stock_cap_bonus
      : cfg.base_stock_cap;
    node.effective_stock_cap = Math.max(
      cfg.min_stock_cap,
      logiCap * (1 - node.devastation * cfg.devastation_cap_penalty)
    );
    node.stock_cap = node.effective_stock_cap; // alias used in showNodeInfo

    // effective_production
    const baseProd = cfg.base_node_production * (1 - node.devastation * cfg.devastation_production_penalty);
    node.effective_production = node.spice_flow + Math.max(cfg.min_node_production, baseProd);

    // flip_count_in_window
    const hist = node.flip_tick_history || [];
    node.flip_count_in_window = hist.filter(t => (tick - t) < cfg.devastation_window_size).length;

    // faction accumulators
    if (ownerId && ownerId in factions) {
      fNodeCount[ownerId]++;
      fTotalSpice[ownerId]  += node.spice_stock;
      fSpiceIncome[ownerId] += node.spice_flow;
    }
  }

  // Derive per-faction fields
  for (const [fid, faction] of Object.entries(factions)) {
    faction.node_count   = fNodeCount[fid]   || 0;
    faction.total_spice  = Math.round(fTotalSpice[fid]  * 100) / 100;
    faction.spice_income = fSpiceIncome[fid] || 0;

    // perceived_relations: true_rel + diplo_bias_strength * max(0, targetDiplo - observerDiplo)
    const observerDiplo = faction.tech ? faction.tech.diplo : 0;
    const perceivedRelations = {};
    for (const [otherId, other] of Object.entries(factions)) {
      if (otherId === fid) continue;
      const trueRel = relationBetween(fid, otherId);
      if (trueRel === null) continue;
      const targetDiplo = other.tech ? other.tech.diplo : 0;
      const gap = Math.max(0, targetDiplo - observerDiplo);
      const perceived = Math.min(1, Math.max(0, trueRel + cfg.diplo_bias_strength * gap));
      perceivedRelations[otherId] = Math.round(perceived * 1000) / 1000;
    }
    faction.perceived_relations = perceivedRelations;
  }

  return raw;
}

// ─────────────────────────────────────────────────────────── //
// Rendering                                                   //
// ─────────────────────────────────────────────────────────── //

function renderGraph(state) {
  // ── Topology change → clear overrides + re-run force layout ─ //
  const topoKey = topologyKey(state.nodes, state.edges);
  if (topoKey !== lastTopologyKey) {
    lastTopologyKey = topoKey;
    const nodeSet = new Set(state.nodes.map(n => n.node_id));
    for (const id of Object.keys(nodeOverrides)) {
      if (!pinnedNodes.has(id)) delete nodeOverrides[id];
    }
    for (const id of [...pinnedNodes]) {
      if (!nodeSet.has(id)) pinnedNodes.delete(id);
    }
    selectedNodeId = null;
    hideNodeInfo();
    runForceLayout(state.nodes, state.edges);
  }

  const nodeMap = {};
  for (const n of state.nodes) nodeMap[n.node_id] = n;

  // Adaptive readability mode
  const denseGraph = state.nodes.length >= 22;
  const compactViewport = svgEl.clientWidth < 920;
  const compactMode = denseGraph || compactViewport;

  const nodeRadius = state.nodes.length >= 30 ? 14 : state.nodes.length >= 22 ? 17 : NODE_R;
  const capitalRadius = nodeRadius + (compactMode ? 3 : 5);

  factionColors = {};
  for (const [fid, f] of Object.entries(state.factions)) {
    factionColors[fid] = f.color;
  }

  const degree = {};
  for (const n of state.nodes) degree[n.node_id] = 0;
  for (const e of state.edges) {
    degree[e.a] = (degree[e.a] || 0) + 1;
    degree[e.b] = (degree[e.b] || 0) + 1;
  }

  // ── Edges ──────────────────────────────────────────────── //
  edgesLayer.innerHTML = "";

  const flows = state.edges.map(e => e.max_flow).filter(v => v != null);
  const maxFlow = flows.length ? Math.max(...flows) : 1;
  const minFlow = flows.length ? Math.min(...flows) : 1;
  const flowRange = maxFlow - minFlow || 1;

  for (const edge of state.edges) {
    const a = nodeMap[edge.a];
    const b = nodeMap[edge.b];
    if (!a || !b) continue;
    const pa = nodePos(a);
    const pb = nodePos(b);
    const t = edge.max_flow != null ? (edge.max_flow - minFlow) / flowRange : 0.5;
    const strokeWidth = (1.5 + t * 2.5).toFixed(1);
    const strokeColor = edge.max_flow != null
      ? capacityColor(edge.max_flow, minFlow, maxFlow)
      : "rgb(120, 120, 120)";
    const dx = pb.cx - pa.cx;
    const dy = pb.cy - pa.cy;
    const len = Math.hypot(dx, dy);

    const crowded = (degree[edge.a] || 0) >= 5 || (degree[edge.b] || 0) >= 5;
    const shortEdge = len < 120;
    let pathD = `M ${pa.cx} ${pa.cy} L ${pb.cx} ${pb.cy}`;
    if (!crowded && !shortEdge) {
      const seed = edgeSeed(edge.a, edge.b);
      const sign = (seed % 2 === 0) ? 1 : -1;
      const bendScale = ((seed % 1000) / 1000.0) * 0.35 + 0.15;
      const bendMag = Math.min(28, len * 0.09 * bendScale);
      pathD = describeOrganicEdge(pa, pb, sign, bendMag);
    }

    // Highlight edges connected to the selected node
    const isSelected = edge.a === selectedNodeId || edge.b === selectedNodeId;
    const path = svgNS("path", {
      class: "edge" + (isSelected ? " edge-selected" : ""),
      d: pathD,
      stroke: isSelected ? "#ffffff99" : strokeColor,
      "stroke-width": isSelected ? (parseFloat(strokeWidth) + 1).toFixed(1) : strokeWidth,
    });
    edgesLayer.appendChild(path);
  }

  // ── Nodes ──────────────────────────────────────────────── //
  nodesLayer.innerHTML = "";
  labelsLayer.innerHTML = "";

  const capitals = new Set(
    Object.values(state.factions).map(f => f.capital_id)
  );

  for (const node of state.nodes) {
    const { cx, cy } = nodePos(node);
    const r = capitals.has(node.node_id) ? capitalRadius : nodeRadius;
    const isCapital = capitals.has(node.node_id);
    const isSelected = node.node_id === selectedNodeId;
    const isPinned = pinnedNodes.has(node.node_id);

    // ── Pressure arc ──
    const flipThreshold = state.config.flip_threshold;
    const pressureFraction = Math.min(1.0, node.pressure_accumulated / flipThreshold);
    if (pressureFraction > 0.01) {
      const startAngle = -Math.PI / 2;
      const endAngle   = startAngle + pressureFraction * 2 * Math.PI;
      const arc = svgNS("path", {
        class: "pressure-ring",
        d: describeArc(cx, cy, r + 5, startAngle, endAngle),
      });
      nodesLayer.appendChild(arc);
    }

    // ── Devastation arc (outer ring, rose-red) ──
    const devastation = typeof node.devastation === "number" ? node.devastation : 0;
    if (devastation > 0.01) {
      const startAngle = -Math.PI / 2;
      const endAngle   = startAngle + devastation * 2 * Math.PI;
      const arc = svgNS("path", {
        class: "devastation-ring",
        d: describeArc(cx, cy, r + 10, startAngle, endAngle),
      });
      nodesLayer.appendChild(arc);
    }

    // ── Selection ring ──
    if (isSelected) {
      const ring = svgNS("circle", {
        cx, cy, r: r + 8,
        fill: "none",
        stroke: "#ffffff",
        "stroke-width": "2",
        "stroke-dasharray": "4 3",
        "pointer-events": "none",
      });
      nodesLayer.appendChild(ring);
    }

    // ── Pin indicator (small dot) ──
    if (isPinned && !isSelected) {
      const pin = svgNS("circle", {
        cx: cx + r - 3, cy: cy - r + 3, r: "4",
        fill: "#f59e0b",
        "pointer-events": "none",
      });
      nodesLayer.appendChild(pin);
    }

    // ── Circle ──
    const circle = svgNS("circle", {
      class: "node-circle" + (isCapital ? " capital" : "") + (isSelected ? " selected" : ""),
      cx, cy, r,
      fill: node.color || "#3a3f47",
    });

    // Drag / click handler
    circle.addEventListener("pointerdown", (e) => {
      e.stopPropagation();
      dragMoved = false;
      const pt = svgPoint(e);
      const ov = nodeOverrides[node.node_id] || { x: node.x, y: node.y };
      dragState = { nodeId: node.node_id, startSvgX: pt.x, startSvgY: pt.y, startNX: ov.x, startNY: ov.y };
      svgEl.setPointerCapture(e.pointerId);
    });

    nodesLayer.appendChild(circle);

    // ── Labels ──
    const idLabel = svgNS("text", { class: "node-label", x: cx, y: cy - 4 });
    if (!compactMode || isCapital) {
      idLabel.textContent = node.node_id.replace("node-", "");
      labelsLayer.appendChild(idLabel);
    }

    const spiceLabel = svgNS("text", { class: "node-spice", x: cx, y: cy + 7 });
    const stock = node.spice_stock != null ? Math.round(node.spice_stock) : "";
    if (!compactMode || isCapital) {
      spiceLabel.textContent = compactMode ? `♦${stock}` : `♦${node.spice_flow} [${stock}]`;
      labelsLayer.appendChild(spiceLabel);
    }
  }
}

function renderFactions(state) {
  factionList.innerHTML = "";
  const sortedFactions = Object.values(state.factions)
    .filter(f => !f.is_eliminated && (f.node_count ?? 0) > 0)
    .sort((a, b) => b.node_count - a.node_count);

  for (const f of sortedFactions) {
    const card = document.createElement("div");
    card.className = "faction-card";

    const isCapital = state.factions[f.faction_id]?.capital_id;
    const zValue = f.behavior?.centralization ?? "-";
    const meanRelation = averageRelationForFaction(state, f.faction_id);
    const symbolicMode = f.symbolic?.mode ?? "-";
    const symbolicGoal = f.symbolic?.goal_id ?? "-";
    const symbolicStrategy = f.symbolic?.strategy_id ?? "-";
    const tech = f.tech || { diplo: 0, cohe: 0, logi: 0 };
    card.innerHTML = `
      <div class="faction-card-header">
        <div class="faction-color-dot" style="background:${f.color}"></div>
        <span class="faction-name">${f.faction_id}${isCapital ? " ★" : ""}</span>
      </div>
      <div class="faction-stats">
        <span>Nodes: ${f.node_count}</span>
        <span>Spice: ${typeof f.total_spice === 'number' ? f.total_spice.toFixed(1) : '—'}</span>
        <span>Income: +${f.spice_income}/tick</span>
      </div>
      <div class="faction-stats">
        <span>E:${f.behavior?.engagement_threshold ?? "-"}</span>
        <span>C:${f.behavior?.concentration ?? "-"}</span>
        <span>L:${f.behavior?.liquidity_preference ?? "-"}</span>
        <span>O:${f.behavior?.objective_bias ?? "-"}</span>
        <span>Z:${zValue}</span>
      </div>
      <div class="faction-stats">
        <span>Ravg: ${meanRelation == null ? "-" : meanRelation.toFixed(2)}</span>
      </div>
      <div class="faction-stats">
        <span class="tech-inline-diplo">D:${tech.diplo.toFixed(3)}</span>
        <span class="tech-inline-cohe">C:${tech.cohe.toFixed(3)}</span>
        <span class="tech-inline-logi">L:${tech.logi.toFixed(3)}</span>
      </div>
      <div class="faction-stats">
        <span>Goal: ${symbolicMode}</span>
        <span title="${symbolicGoal}">G:${symbolicGoal}</span>
        <span title="${symbolicStrategy}">S:${symbolicStrategy}</span>
      </div>
      <div class="faction-genome" title="Genome">${f.genome_str}</div>
    `;
    factionList.appendChild(card);
  }
}

function renderEventLog(state) {
  eventList.innerHTML = "";
  const events = [...state.event_log].reverse();
  for (const evt of events) {
    const li = document.createElement("li");
    li.textContent = evt;
    if (evt.includes("SECESSION")) li.className = "secession";
    else if (evt.includes("flipped"))   li.className = "flip";
    else if (evt.includes("VICTORY"))   li.className = "victory";
    eventList.appendChild(li);
  }
}

function renderRelations(state) {
  if (!relationsMeta || !relationsList) return;

  const activeIds = activeFactionIds(state);
  const relations = (Array.isArray(state.relations) ? state.relations : [])
    .filter(r => activeIds.has(r.a) && activeIds.has(r.b));
  if (!relations.length) {
    relationsMeta.textContent = "no known relations";
    relationsList.innerHTML = "<div class=\"relations-empty\">No faction pair has established contact yet.</div>";
    return;
  }

  const avg = relations.reduce((acc, r) => acc + (typeof r.value === "number" ? r.value : 0), 0) / relations.length;
  relationsMeta.textContent = `${relations.length} pair${relations.length !== 1 ? "s" : ""} · avg ${avg.toFixed(2)}`;

  const ordered = [...relations].sort((a, b) => (b.value ?? 0) - (a.value ?? 0));
  relationsList.innerHTML = ordered.map((r) => {
    const value = typeof r.value === "number" ? r.value : 0;
    const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
    return `
      <div class="relation-row">
        <div class="relation-head">
          <span class="relation-pair">${r.a} ⇄ ${r.b}</span>
          <span class="relation-value">${value.toFixed(2)}</span>
        </div>
        <div class="relation-bar">
          <div class="relation-bar-fill" style="width:${pct}%"></div>
        </div>
      </div>
    `;
  }).join("");
}

function renderSymbolicPanel(state) {
  if (!symbolicMeta || !symbolicList) return;

  const activeIds = activeFactionIds(state);
  const activeFactions = Object.values(state.factions || {})
    .filter(f => activeIds.has(f.faction_id))
    .sort((a, b) => b.node_count - a.node_count);

  const rows = activeFactions
    .filter(f => f.symbolic)
    .map((f) => {
      const mode = f.symbolic.mode ?? "-";
      const goal = f.symbolic.goal_id ?? "-";
      const strategy = f.symbolic.strategy_id ?? "-";
      const priority = typeof f.symbolic.goal_priority === "number"
        ? f.symbolic.goal_priority.toFixed(2)
        : "-";
      return `
        <div class="symbolic-row">
          <div class="symbolic-head">
            <span class="symbolic-faction">${f.faction_id}</span>
            <span class="symbolic-mode">${mode}</span>
          </div>
          <div class="symbolic-stats">
            <span>Priority: ${priority}</span>
            <span title="${goal}">G:${goal}</span>
            <span title="${strategy}">S:${strategy}</span>
          </div>
        </div>
      `;
    });

  if (!rows.length) {
    symbolicMeta.textContent = "no active intents";
    symbolicList.innerHTML = "<div class=\"symbolic-empty\">No symbolic plan is currently available.</div>";
    return;
  }

  symbolicMeta.textContent = `${rows.length} active intent${rows.length !== 1 ? "s" : ""}`;
  symbolicList.innerHTML = rows.join("");
}

function renderTechPanel(state) {
  if (!techMeta || !techList) return;

  const activeIds = activeFactionIds(state);
  const activeFactions = Object.values(state.factions || {})
    .filter(f => activeIds.has(f.faction_id))
    .sort((a, b) => b.node_count - a.node_count);

  if (!activeFactions.length) {
    techMeta.textContent = "no data";
    techList.innerHTML = "";
    return;
  }

  techMeta.textContent = `${activeFactions.length} faction${activeFactions.length !== 1 ? "s" : ""}`;

  function techBar(val, cssVar) {
    const pct = Math.round(Math.max(0, Math.min(1, val)) * 100);
    return `<div class="tech-bar"><div class="tech-bar-fill" style="width:${pct}%;background:${cssVar}"></div></div>`;
  }

  techList.innerHTML = activeFactions.map(f => {
    const tech = f.tech || { diplo: 0, cohe: 0, logi: 0 };
    const inv  = f.tech_investment || { diplo: 0, cohe: 0, logi: 0 };
    const α    = f.tech_alpha || { diplo: 0, cohe: 0, logi: 0 };
    return `
      <div class="tech-row">
        <div class="tech-head">
          <span class="tech-dot" style="background:${f.color}"></span>
          <span class="tech-faction-name">${f.faction_id}</span>
        </div>
        <div class="tech-axis">
          <span class="tech-label" style="color:var(--tech-diplo)">Diplo</span>
          ${techBar(tech.diplo, "var(--tech-diplo)")}
          <span class="tech-val">${tech.diplo.toFixed(3)}</span>
          <span class="tech-inv">+${inv.diplo.toFixed(4)}</span>
        </div>
        <div class="tech-axis">
          <span class="tech-label" style="color:var(--tech-cohe)">Cohé</span>
          ${techBar(tech.cohe, "var(--tech-cohe)")}
          <span class="tech-val">${tech.cohe.toFixed(3)}</span>
          <span class="tech-inv">+${inv.cohe.toFixed(4)}</span>
        </div>
        <div class="tech-axis">
          <span class="tech-label" style="color:var(--tech-logi)">Logi</span>
          ${techBar(tech.logi, "var(--tech-logi)")}
          <span class="tech-val">${tech.logi.toFixed(3)}</span>
          <span class="tech-inv">+${inv.logi.toFixed(4)}</span>
        </div>
        <div class="tech-alpha">
          α D:${α.diplo.toFixed(2)} C:${α.cohe.toFixed(2)} L:${α.logi.toFixed(2)}
        </div>
      </div>
    `;
  }).join("");
}

// ── Node info tooltip ──────────────────────────────────────── //

function showNodeInfo(node, state) {
  const panel = document.getElementById("node-info");
  if (!panel) return;

  const faction = Object.values(state.factions || {}).find(f => f.color === node.color);
  const factionName = faction ? faction.faction_id : "Unclaimed";
  const capitals = new Set(Object.values(state.factions || {}).map(f => f.capital_id));
  const isCapital = capitals.has(node.node_id);
  const linkCount = (state.edges || []).filter(e => e.a === node.node_id || e.b === node.node_id).length;
  const flipThreshold = state.config?.flip_threshold ?? 1;
  const pressurePct = Math.min(100, (node.pressure_accumulated / flipThreshold * 100)).toFixed(0);
  const stock = node.spice_stock != null ? Math.round(node.spice_stock) : 0;
  const devasPct = typeof node.devastation === "number" ? (node.devastation * 100).toFixed(0) + "%" : "—";
  const effCap = node.effective_stock_cap != null ? node.effective_stock_cap.toFixed(1) : "—";
  const effProd = node.effective_production != null ? node.effective_production.toFixed(2) : "—";
  const flipsWin = node.flip_count_in_window ?? "—";

  document.getElementById("node-info-content").innerHTML = `
    <div class="ni-title">${node.node_id}${isCapital ? " ★" : ""}</div>
    <div class="ni-row">Owner <span style="color:${node.color};font-weight:600">${factionName}</span></div>
    <div class="ni-row">Income <span>♦${node.spice_flow}/tick</span></div>
    <div class="ni-row">Stock <span>♦${stock}</span></div>
    <div class="ni-row">Links <span>${linkCount}</span></div>
    <div class="ni-row">Pressure <span>${pressurePct}%</span></div>
    <div class="ni-row">Devastation <span class="devas-value">${devasPct}</span></div>
    <div class="ni-row">Eff. cap <span>${effCap}</span></div>
    <div class="ni-row">Eff. prod <span>${effProd}</span></div>
    <div class="ni-row">Flips (win) <span>${flipsWin}</span></div>
    <div class="ni-row">Pinned <span>${pinnedNodes.has(node.node_id) ? "yes" : "no"}</span></div>
  `;

  // Position near the node
  const ov = nodeOverrides[node.node_id] || { x: node.x, y: node.y };
  const panelPos = svgViewboxToPanel(ov.x * SVG_W, ov.y * SVG_H);
  const panelEl  = document.getElementById("map-panel");
  const maxLeft  = panelEl.clientWidth  - 180;
  const maxTop   = panelEl.clientHeight - 280;
  panel.style.left = Math.max(4, Math.min(maxLeft, panelPos.x + 20)) + "px";
  panel.style.top  = Math.max(4, Math.min(maxTop,  panelPos.y - 20)) + "px";
  panel.classList.remove("hidden");
}

function hideNodeInfo() {
  const panel = document.getElementById("node-info");
  if (panel) panel.classList.add("hidden");
}

// ── SVG-level pointer handlers for drag ───────────────────── //

svgEl.addEventListener("pointermove", (e) => {
  if (!dragState) return;
  e.preventDefault();
  const pt = svgPoint(e);
  const dx = pt.x - dragState.startSvgX;
  const dy = pt.y - dragState.startSvgY;
  if (!dragMoved && Math.hypot(dx, dy) > 5) dragMoved = true;
  if (!dragMoved) return;
  const nx = Math.max(0.03, Math.min(0.97, dragState.startNX + dx / SVG_W));
  const ny = Math.max(0.03, Math.min(0.97, dragState.startNY + dy / SVG_H));
  nodeOverrides[dragState.nodeId] = { x: nx, y: ny };
  pinnedNodes.add(dragState.nodeId);
  if (lastState) renderGraph(lastState);
});

svgEl.addEventListener("pointerup", (e) => {
  if (!dragState) return;
  if (!dragMoved) {
    // Treat as click: toggle selection
    const clickedId = dragState.nodeId;
    selectedNodeId = selectedNodeId === clickedId ? null : clickedId;
    if (selectedNodeId && lastState) {
      const node = lastState.nodes.find(n => n.node_id === clickedId);
      if (node) showNodeInfo(node, lastState);
    } else {
      hideNodeInfo();
    }
    if (lastState) renderGraph(lastState);
  }
  dragState = null;
  dragMoved = false;
});

svgEl.addEventListener("pointercancel", () => {
  dragState = null;
  dragMoved = false;
});

function render(state) {
  lastState = state;
  tickCounter.textContent = `Tick: ${state.tick}`;

  const canStepBack = (state.history_size ?? 0) > 0;
  btnStepBack.disabled = !canStepBack;
  btnReverseRun.disabled = !canStepBack;

  if (state.game_over) {
    statusText.textContent = state.winner_id
      ? `🏆 ${state.winner_id} wins!`
      : "Game over";
    statusText.className = "victory";
    stopAutorun();
    btnStep.disabled = true;
    btnAutorun.disabled = true;
  } else {
    const activeCount = Object.values(state.factions)
      .filter(f => !f.is_eliminated && (f.node_count ?? 0) > 0).length;
    statusText.textContent = `${activeCount} faction${activeCount !== 1 ? "s" : ""} active · ${relationSummary(state)}`;
    statusText.className = "";
    btnStep.disabled = false;
    btnAutorun.disabled = false;
  }

  renderGraph(state);
  renderFactions(state);
  renderRelations(state);
  renderSymbolicPanel(state);
  renderTechPanel(state);
  renderEventLog(state);
}

// ─────────────────────────────────────────────────────────── //
// API calls                                                   //
// ─────────────────────────────────────────────────────────── //

async function fetchState() {
  const res = await fetch(`${API}/api/state`);
  return computeDerivedState(await res.json());
}

async function postStep() {
  const res = await fetch(`${API}/api/step`, { method: "POST" });
  return computeDerivedState(await res.json());
}

async function postStepBack() {
  const res = await fetch(`${API}/api/step_back`, { method: "POST" });
  return computeDerivedState(await res.json());
}

async function postReset(config = {}) {
  const res = await fetch(`${API}/api/reset`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  return computeDerivedState(await res.json());
}

// ─────────────────────────────────────────────────────────── //
// Auto-run                                                    //
// ─────────────────────────────────────────────────────────── //

function getIntervalMs() {
  return parseInt(speedSlider.value, 10);
}

function startReverseRun() {
  if (reverseTimer !== null) return;
  stopAutorun();
  btnReverseRun.textContent = "⏸ Pause";
  btnReverseRun.classList.add("running");

  async function tick() {
    if (reverseTimer === null) return;
    const state = await postStepBack();
    render(state);
    if ((state.history_size ?? 0) > 0) {
      reverseTimer = setTimeout(tick, getIntervalMs());
    } else {
      stopReverseRun();
    }
  }
  reverseTimer = setTimeout(tick, 0);
}

function stopReverseRun() {
  if (reverseTimer !== null) {
    clearTimeout(reverseTimer);
    reverseTimer = null;
  }
  btnReverseRun.textContent = "◀ Reverse";
  btnReverseRun.classList.remove("running");
}

function toggleReverseRun() {
  if (reverseTimer !== null) stopReverseRun();
  else startReverseRun();
}

function startAutorun() {
  if (autorunTimer !== null) return;
  stopReverseRun();
  btnAutorun.textContent = "⏸ Pause";
  btnAutorun.classList.add("running");

  async function tick() {
    if (autorunTimer === null) return;  // stopped
    const state = await postStep();
    render(state);
    if (!state.game_over) {
      autorunTimer = setTimeout(tick, getIntervalMs());
    } else {
      stopAutorun();
    }
  }
  autorunTimer = setTimeout(tick, 0);
}

function stopAutorun() {
  if (autorunTimer !== null) {
    clearTimeout(autorunTimer);
    autorunTimer = null;
  }
  btnAutorun.textContent = "▶ Auto-run";
  btnAutorun.classList.remove("running");
}

function toggleAutorun() {
  if (autorunTimer !== null) {
    stopAutorun();
  } else {
    startAutorun();
  }
}

// ─────────────────────────────────────────────────────────── //
// Config form                                                 //
// ─────────────────────────────────────────────────────────── //

function readConfigForm() {
  const fd = new FormData(configForm);
  const cfg = {};
  for (const [key, val] of fd.entries()) {
    if (key === "layout" || key === "graph_mode" || key === "geography_preset" || key === "perception_mode") {
      cfg[key] = val;
      continue;
    }
    const num = parseFloat(val);
    cfg[key] = isNaN(num) ? val : num;
  }
  // Coerce integer fields
  for (const intKey of ["num_nodes", "num_factions", "seed", "min_spice_flow", "max_spice_flow", "genome_length", "max_ticks", "tech_rnd_history_window", "devastation_window_size"]) {
    if (intKey in cfg) cfg[intKey] = Math.round(cfg[intKey]);
  }
  return cfg;
}

function populateConfigForm(config) {
  const fields = configForm.querySelectorAll("input, select");
  for (const field of fields) {
    const val = config[field.name];
    if (val !== undefined) field.value = val;
  }
}

// ─────────────────────────────────────────────────────────── //
// Event wiring                                               //
// ─────────────────────────────────────────────────────────── //

document.querySelectorAll(".side-tab").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".side-tab").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    const tab = btn.dataset.tab;
    document.getElementById("tab-sim").classList.toggle("hidden", tab !== "sim");
    document.getElementById("tab-about").classList.toggle("hidden", tab !== "about");
  });
});

document.getElementById("node-info-close").addEventListener("click", () => {
  selectedNodeId = null;
  hideNodeInfo();
  if (lastState) renderGraph(lastState);
});

document.getElementById("btn-reset-layout").addEventListener("click", () => {
  for (const id of Object.keys(nodeOverrides)) delete nodeOverrides[id];
  pinnedNodes.clear();
  selectedNodeId = null;
  hideNodeInfo();
  if (lastState) {
    runForceLayout(lastState.nodes, lastState.edges);
    renderGraph(lastState);
  }
});

btnStepBack.addEventListener("click", async () => {
  stopAutorun();
  stopReverseRun();
  const state = await postStepBack();
  render(state);
});

btnStep.addEventListener("click", async () => {
  stopAutorun();
  stopReverseRun();
  const state = await postStep();
  render(state);
});

btnReverseRun.addEventListener("click", () => {
  toggleReverseRun();
});

btnAutorun.addEventListener("click", () => {
  toggleAutorun();
});

btnReset.addEventListener("click", async () => {
  stopAutorun();
  const cfg = readConfigForm();
  const state = await postReset(cfg);
  btnStep.disabled = false;
  btnAutorun.disabled = false;
  statusText.className = "";
  render(state);
});

configForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  stopAutorun();
  const cfg = readConfigForm();
  const state = await postReset(cfg);
  btnStep.disabled = false;
  btnAutorun.disabled = false;
  statusText.className = "";
  render(state);
});

speedSlider.addEventListener("input", () => {
  const ms = getIntervalMs();
  speedLabel.textContent = (ms / 1000).toFixed(1) + " s";
  // If auto-running, restart timer with new interval
  if (autorunTimer !== null) {
    stopAutorun();
    startAutorun();
  }
});

// ─────────────────────────────────────────────────────────── //
// Bootstrap                                                   //
// ─────────────────────────────────────────────────────────── //

(async () => {
  try {
    const state = await fetchState();
    populateConfigForm(state.config);
    render(state);
  } catch (err) {
    statusText.textContent = "Could not connect to server — is it running?";
    statusText.style.color = "var(--danger)";
    console.error(err);
  }
})();
