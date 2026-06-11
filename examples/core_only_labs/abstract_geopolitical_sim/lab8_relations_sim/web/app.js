/**
 * app.js — Lab 8 Relations Simulation client
 *
 * Responsibilities:
 *  - Fetch /api/state and render SVG graph (nodes, edges, ownership colours)
 *  - Step (manual) and auto-run with configurable speed
 *  - Faction legend sidebar: total spice (node-resident), income, move orders
 *  - Config form submission → POST /api/reset
 *  - Pressure ring arcs on nodes to show conquest progress
 *  - Node label shows spice_stock held at that node
 *  - Edge thickness reflects link max_flow capacity
 */

"use strict";

const API = "http://127.0.0.1:8772";  // Lab 8 server port

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
const speedSlider  = document.getElementById("speed-slider");
const speedLabel   = document.getElementById("speed-label");
const btnStep      = document.getElementById("btn-step");
const btnAutorun   = document.getElementById("btn-autorun");
const btnReset     = document.getElementById("btn-reset");
const configForm   = document.getElementById("config-form");

// ─────────────────────────────────────────────────────────── //
// State                                                       //
// ─────────────────────────────────────────────────────────── //

let autorunTimer   = null;
let lastState      = null;
let factionColors  = {};  // faction_id → hex colour (cached for edge colouring)

// ─────────────────────────────────────────────────────────── //
// Utility                                                     //
// ─────────────────────────────────────────────────────────── //

function svgNS(tag, attrs = {}) {
  const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  return el;
}

function nodePos(node) {
  return {
    cx: Math.round(node.x * SVG_W),
    cy: Math.round(node.y * SVG_H),
  };
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

function averageRelationForFaction(state, factionId) {
  const relations = Array.isArray(state.relations) ? state.relations : [];
  const values = relations
    .filter(r => r.a === factionId || r.b === factionId)
    .map(r => (typeof r.value === "number" ? r.value : 0));
  if (!values.length) return null;
  const mean = values.reduce((acc, v) => acc + v, 0) / values.length;
  return mean;
}

function relationSummary(state) {
  const relations = Array.isArray(state.relations) ? state.relations : [];
  if (!relations.length) return "no known relations";
  const mean = relations.reduce((acc, r) => {
    const v = typeof r.value === "number" ? r.value : 0;
    return acc + v;
  }, 0) / relations.length;
  return `${relations.length} known pair${relations.length !== 1 ? "s" : ""}, avg R ${mean.toFixed(2)}`;
}

// ─────────────────────────────────────────────────────────── //
// Rendering                                                   //
// ─────────────────────────────────────────────────────────── //

function renderGraph(state) {
  const nodeMap = {};
  for (const n of state.nodes) nodeMap[n.node_id] = n;

  // Adaptive readability mode: reduce visual density when many nodes are present
  // or when viewport is compact.
  const denseGraph = state.nodes.length >= 22;
  const compactViewport = svgEl.clientWidth < 920;
  const compactMode = denseGraph || compactViewport;

  const nodeRadius = state.nodes.length >= 30 ? 14 : state.nodes.length >= 22 ? 17 : NODE_R;
  const capitalRadius = nodeRadius + (compactMode ? 3 : 5);

  // Update faction colour cache
  factionColors = {};
  for (const [fid, f] of Object.entries(state.factions)) {
    factionColors[fid] = f.color;
  }

  // Endpoint degree map used to preserve readability in dense areas.
  const degree = {};
  for (const n of state.nodes) degree[n.node_id] = 0;
  for (const e of state.edges) {
    degree[e.a] = (degree[e.a] || 0) + 1;
    degree[e.b] = (degree[e.b] || 0) + 1;
  }

  // ── Edges ──────────────────────────────────────────────── //
  edgesLayer.innerHTML = "";

  // Determine max_flow range for scaling edge thickness
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
    // Scale stroke width 1.5–4 based on max_flow
    const t = edge.max_flow != null ? (edge.max_flow - minFlow) / flowRange : 0.5;
    const strokeWidth = (1.5 + t * 2.5).toFixed(1);
    const strokeColor = edge.max_flow != null
      ? capacityColor(edge.max_flow, minFlow, maxFlow)
      : "rgb(120, 120, 120)";
    const dx = pb.cx - pa.cx;
    const dy = pb.cy - pa.cy;
    const len = Math.hypot(dx, dy);

    // Readability rule:
    // - Keep straight when local density is high or edge is short.
    // - Otherwise apply a mild deterministic bend for an organic look.
    const crowded = (degree[edge.a] || 0) >= 5 || (degree[edge.b] || 0) >= 5;
    const shortEdge = len < 120;
    let pathD = `M ${pa.cx} ${pa.cy} L ${pb.cx} ${pb.cy}`;
    if (!crowded && !shortEdge) {
      const seed = edgeSeed(edge.a, edge.b);
      const sign = (seed % 2 === 0) ? 1 : -1;
      const bendScale = ((seed % 1000) / 1000.0) * 0.35 + 0.15; // 0.15..0.50
      const bendMag = Math.min(28, len * 0.09 * bendScale);
      pathD = describeOrganicEdge(pa, pb, sign, bendMag);
    }

    const path = svgNS("path", {
      class: "edge",
      d: pathD,
      stroke: strokeColor,
      "stroke-width": strokeWidth,
    });
    edgesLayer.appendChild(path);
  }

  // ── Nodes ──────────────────────────────────────────────── //
  nodesLayer.innerHTML = "";
  labelsLayer.innerHTML = "";

  // Identify capitals
  const capitals = new Set(
    Object.values(state.factions).map(f => f.capital_id)
  );

  for (const node of state.nodes) {
    const { cx, cy } = nodePos(node);
    const r = capitals.has(node.node_id) ? capitalRadius : nodeRadius;
    const isCapital = capitals.has(node.node_id);

    // ── Pressure arc (ring) ──
    const flipThreshold = state.config.flip_threshold;
    const pressureFraction = Math.min(1.0, node.pressure_accumulated / flipThreshold);
    if (pressureFraction > 0.01) {
      const startAngle = -Math.PI / 2;
      const endAngle   = startAngle + pressureFraction * 2 * Math.PI;
      const arcR = r + 5;
      const arcPath = describeArc(cx, cy, arcR, startAngle, endAngle);
      const arc = svgNS("path", {
        class: "pressure-ring",
        d: arcPath,
      });
      nodesLayer.appendChild(arc);
    }

    // ── Circle ──
    const circle = svgNS("circle", {
      class: "node-circle" + (isCapital ? " capital" : ""),
      cx, cy, r,
      fill: node.color || "#3a3f47",
    });
    nodesLayer.appendChild(circle);

    // ── Labels ──
    const idLabel = svgNS("text", {
      class: "node-label",
      x: cx, y: cy - 4,
    });
    // In compact mode, only show id labels for capitals to reduce overlap.
    if (!compactMode || isCapital) {
      idLabel.textContent = node.node_id.replace("node-", "");
      labelsLayer.appendChild(idLabel);
    }

    const spiceLabel = svgNS("text", {
      class: "node-spice",
      x: cx, y: cy + 7,
    });
    // Show node stock (logistics) rather than income alone
    const stock = node.spice_stock != null ? Math.round(node.spice_stock) : "";
    // In compact mode, keep spice labels only for capitals.
    if (!compactMode || isCapital) {
      spiceLabel.textContent = compactMode
        ? `♦${stock}`
        : `♦${node.spice_flow} [${stock}]`;
      labelsLayer.appendChild(spiceLabel);
    }
  }
}

function renderFactions(state) {
  factionList.innerHTML = "";
  const sortedFactions = Object.values(state.factions)
    .sort((a, b) => b.node_count - a.node_count);

  for (const f of sortedFactions) {
    const card = document.createElement("div");
    card.className = "faction-card" + (f.is_eliminated ? " eliminated" : "");

    const isCapital = state.factions[f.faction_id]?.capital_id;
    const zValue = f.behavior?.centralization ?? "-";
    const meanRelation = averageRelationForFaction(state, f.faction_id);
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

  const relations = Array.isArray(state.relations) ? state.relations : [];
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

function render(state) {
  lastState = state;
  tickCounter.textContent = `Tick: ${state.tick}`;

  if (state.game_over) {
    statusText.textContent = state.winner_id
      ? `🏆 ${state.winner_id} wins!`
      : "Game over";
    statusText.className = "victory";
    stopAutorun();
    btnStep.disabled = true;
    btnAutorun.disabled = true;
  } else {
    const factionCount = Object.keys(state.factions).length;
    const activeCount  = Object.values(state.factions).filter(f => !f.is_eliminated).length;
    statusText.textContent = `${activeCount} faction${activeCount !== 1 ? "s" : ""} active · ${relationSummary(state)}`;
    statusText.className = "";
    btnStep.disabled = false;
    btnAutorun.disabled = false;
  }

  renderGraph(state);
  renderFactions(state);
  renderRelations(state);
  renderEventLog(state);
}

// ─────────────────────────────────────────────────────────── //
// API calls                                                   //
// ─────────────────────────────────────────────────────────── //

async function fetchState() {
  const res = await fetch(`${API}/api/state`);
  return res.json();
}

async function postStep() {
  const res = await fetch(`${API}/api/step`, { method: "POST" });
  return res.json();
}

async function postReset(config = {}) {
  const res = await fetch(`${API}/api/reset`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  return res.json();
}

// ─────────────────────────────────────────────────────────── //
// Auto-run                                                    //
// ─────────────────────────────────────────────────────────── //

function getIntervalMs() {
  return parseInt(speedSlider.value, 10);
}

function startAutorun() {
  if (autorunTimer !== null) return;
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
  for (const intKey of ["num_nodes", "num_factions", "seed", "min_spice_flow", "max_spice_flow", "genome_length", "max_ticks"]) {
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

btnStep.addEventListener("click", async () => {
  stopAutorun();
  const state = await postStep();
  render(state);
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
