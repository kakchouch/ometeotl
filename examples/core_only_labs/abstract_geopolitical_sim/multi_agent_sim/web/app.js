/**
 * app.js — Multi-Agent Graph Simulation client
 *
 * Responsibilities:
 *  - Fetch /api/state and render SVG graph (nodes, edges, ownership colours)
 *  - Step (manual) and auto-run with configurable speed
 *  - Faction legend sidebar with genome display
 *  - Config form submission → POST /api/reset
 *  - Pressure ring arcs on nodes to show conquest progress
 */

"use strict";

const API = "http://127.0.0.1:8766";

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

// ─────────────────────────────────────────────────────────── //
// Rendering                                                   //
// ─────────────────────────────────────────────────────────── //

function renderGraph(state) {
  const nodeMap = {};
  for (const n of state.nodes) nodeMap[n.node_id] = n;

  // Update faction colour cache
  factionColors = {};
  for (const [fid, f] of Object.entries(state.factions)) {
    factionColors[fid] = f.color;
  }

  // ── Edges ──────────────────────────────────────────────── //
  edgesLayer.innerHTML = "";
  for (const edge of state.edges) {
    const a = nodeMap[edge.a];
    const b = nodeMap[edge.b];
    if (!a || !b) continue;
    const pa = nodePos(a);
    const pb = nodePos(b);
    const line = svgNS("line", {
      class: "edge",
      x1: pa.cx, y1: pa.cy,
      x2: pb.cx, y2: pb.cy,
    });
    edgesLayer.appendChild(line);
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
    const r = capitals.has(node.node_id) ? NODE_R_CAPITAL : NODE_R;
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
    idLabel.textContent = node.node_id.replace("node-", "");
    labelsLayer.appendChild(idLabel);

    const spiceLabel = svgNS("text", {
      class: "node-spice",
      x: cx, y: cy + 7,
    });
    spiceLabel.textContent = `♦${node.spice_flow}`;
    labelsLayer.appendChild(spiceLabel);
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
    card.innerHTML = `
      <div class="faction-card-header">
        <div class="faction-color-dot" style="background:${f.color}"></div>
        <span class="faction-name">${f.faction_id}${isCapital ? " ★" : ""}</span>
      </div>
      <div class="faction-stats">
        <span>Nodes: ${f.node_count}</span>
        <span>Stock: ${Math.round(f.spice_stock)}</span>
        <span>Income: +${f.spice_income}/tick</span>
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
    statusText.textContent = `${activeCount} faction${activeCount !== 1 ? "s" : ""} active`;
    statusText.className = "";
    btnStep.disabled = false;
    btnAutorun.disabled = false;
  }

  renderGraph(state);
  renderFactions(state);
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
    if (key === "layout" || key === "graph_mode") {
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
