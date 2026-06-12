/**
 * app.js — Spatial Map Lab client
 *
 * Renders a grid of rectangular zones as SVG <rect> elements, coloured
 * by actor occupancy (heatmap).  Actors are dots placed at their
 * fractional position within the zone.  Dashed lines connect adjacent
 * zone centroids, mirroring the derived SpaceRelationGraph.
 *
 * Controls: manual step, auto-run with speed slider, config form reset.
 */

"use strict";

const API = "http://127.0.0.1:8790";

// SVG viewport dimensions (must match viewBox in HTML)
const SVG_W = 800;
const SVG_H = 600;
const PADDING = 24;   // px inside SVG edges
const ACTOR_R = 5;    // actor dot radius in SVG px

// ─────────────────────────────────────────────────────────── //
// DOM refs                                                    //
// ─────────────────────────────────────────────────────────── //

const svgEl       = document.getElementById("map-svg");
const edgesLayer  = document.getElementById("edges-layer");
const zonesLayer  = document.getElementById("zones-layer");
const labelsLayer = document.getElementById("labels-layer");
const actorsLayer = document.getElementById("actors-layer");

const tickCounter = document.getElementById("tick-counter");
const statusText  = document.getElementById("status-text");
const eventList   = document.getElementById("event-list");
const statsList   = document.getElementById("stats-list");
const zoneList    = document.getElementById("zone-list");
const speedSlider = document.getElementById("speed-slider");
const speedLabel  = document.getElementById("speed-label");
const btnStep     = document.getElementById("btn-step");
const btnAutorun  = document.getElementById("btn-autorun");
const btnReset    = document.getElementById("btn-reset");
const configForm  = document.getElementById("config-form");

// ─────────────────────────────────────────────────────────── //
// State                                                       //
// ─────────────────────────────────────────────────────────── //

let autorunTimer = null;

// ─────────────────────────────────────────────────────────── //
// SVG helpers                                                 //
// ─────────────────────────────────────────────────────────── //

function svgNS(tag, attrs = {}) {
  const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  return el;
}

/** Map normalised [0,1] world coordinate to SVG px, with padding. */
function toSVG(nx, ny) {
  const usableW = SVG_W - 2 * PADDING;
  const usableH = SVG_H - 2 * PADDING;
  return {
    x: PADDING + nx * usableW,
    y: PADDING + ny * usableH,
  };
}

/**
 * Zone fill colour — interpolates between a dark base (empty) and a
 * bright highlight (fully occupied). Max meaningful occupancy is ~4
 * actors before the colour saturates.
 */
function zoneColor(actorCount) {
  const t = Math.min(1, actorCount / 4);
  // dark slate → bright teal
  const r = Math.round(30  + t * (40  - 30));
  const g = Math.round(45  + t * (180 - 45));
  const b = Math.round(60  + t * (160 - 60));
  return `rgb(${r},${g},${b})`;
}

// ─────────────────────────────────────────────────────────── //
// Rendering                                                   //
// ─────────────────────────────────────────────────────────── //

function renderEdges(state) {
  edgesLayer.innerHTML = "";
  for (const e of state.adjacency_edges) {
    const a = toSVG(e.ax, e.ay);
    const b = toSVG(e.bx, e.by);
    edgesLayer.appendChild(svgNS("line", {
      class: "adj-edge",
      x1: a.x, y1: a.y,
      x2: b.x, y2: b.y,
    }));
  }
}

function renderZones(state) {
  zonesLayer.innerHTML = "";
  labelsLayer.innerHTML = "";

  const usableW = SVG_W - 2 * PADDING;
  const usableH = SVG_H - 2 * PADDING;

  for (const z of state.zones) {
    const sx = PADDING + z.x * usableW;
    const sy = PADDING + z.y * usableH;
    const sw = z.w * usableW;
    const sh = z.h * usableH;
    const cx = PADDING + z.centroid_x * usableW;
    const cy = PADDING + z.centroid_y * usableH;

    const rect = svgNS("rect", {
      class: "zone-rect",
      x: sx, y: sy,
      width: sw, height: sh,
      fill: zoneColor(z.actor_count),
      rx: 4,
    });
    zonesLayer.appendChild(rect);

    // Label (zone short name)
    const lbl = svgNS("text", {
      class: "zone-label",
      x: cx, y: cy - (sh > 40 ? 7 : 0),
    });
    lbl.textContent = z.label;
    labelsLayer.appendChild(lbl);

    // Actor count badge
    if (sh > 28) {
      const cnt = svgNS("text", {
        class: "zone-count",
        x: cx, y: cy + 8,
      });
      cnt.textContent = z.actor_count > 0 ? `×${z.actor_count}` : "";
      labelsLayer.appendChild(cnt);
    }
  }
}

function renderActors(state) {
  actorsLayer.innerHTML = "";
  const usableW = SVG_W - 2 * PADDING;
  const usableH = SVG_H - 2 * PADDING;

  for (const a of state.actors) {
    const sx = PADDING + a.x * usableW;
    const sy = PADDING + a.y * usableH;
    const dot = svgNS("circle", {
      class: "actor-dot",
      cx: sx, cy: sy,
      r: ACTOR_R,
      fill: a.color,
    });
    // Tooltip
    const title = svgNS("title");
    title.textContent = `${a.actor_id} @ ${a.zone_id}`;
    dot.appendChild(title);
    actorsLayer.appendChild(dot);
  }
}

function renderStats(state) {
  const s = state.stats;
  statsList.innerHTML = `
    <div class="stat-row"><span>Zones</span><span>${s.zone_count}</span></div>
    <div class="stat-row"><span>Actors</span><span>${s.actor_count}</span></div>
    <div class="stat-row"><span>Adjacency edges</span><span>${s.adjacency_edge_count}</span></div>
    <div class="stat-row"><span>Actors near centre</span><span>${s.actors_near_world_centre.length}</span></div>
  `;
}

function renderZoneList(state) {
  const occupied = state.zones
    .filter(z => z.actor_count > 0)
    .sort((a, b) => b.actor_count - a.actor_count);

  zoneList.innerHTML = occupied.length
    ? occupied.map(z => `
        <div class="zone-card">
          <span class="zone-card-label">${z.label}</span>
          <span class="zone-card-actors">${z.actors.join(", ")}</span>
          <span class="zone-card-count">${z.actor_count}</span>
        </div>
      `).join("")
    : `<div style="font-size:11px;color:var(--text-muted)">No occupied zones.</div>`;
}

function renderEventLog(state) {
  eventList.innerHTML = "";
  const events = [...state.event_log].reverse();
  for (const evt of events) {
    const li = document.createElement("li");
    li.textContent = evt;
    if (evt.includes("moved"))         li.className = "move";
    else if (evt.includes("tick 0"))   li.className = "init";
    else if (evt.includes("No actors")) li.className = "quiet";
    eventList.appendChild(li);
  }
}

function render(state) {
  tickCounter.textContent = `Tick: ${state.tick}`;

  const maxTicks = state.config.max_ticks;
  if (maxTicks > 0 && state.tick >= maxTicks) {
    statusText.textContent = `Stopped — max ticks (${maxTicks}) reached.`;
    stopAutorun();
  } else {
    const cols = state.config.grid_cols;
    const rows = state.config.grid_rows;
    statusText.textContent = `${cols}×${rows} grid · ${state.stats.actor_count} actors · ${state.stats.adjacency_edge_count} adj. edges`;
  }

  renderEdges(state);
  renderZones(state);
  renderActors(state);
  renderStats(state);
  renderZoneList(state);
  renderEventLog(state);
}

// ─────────────────────────────────────────────────────────── //
// API                                                         //
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
    if (autorunTimer === null) return;
    const state = await postStep();
    render(state);
    const maxTicks = state.config.max_ticks;
    const done = maxTicks > 0 && state.tick >= maxTicks;
    if (!done) {
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
  autorunTimer !== null ? stopAutorun() : startAutorun();
}

// ─────────────────────────────────────────────────────────── //
// Config form                                                 //
// ─────────────────────────────────────────────────────────── //

function readConfigForm() {
  const fd = new FormData(configForm);
  const cfg = {};
  for (const [key, val] of fd.entries()) {
    const num = parseFloat(val);
    cfg[key] = isNaN(num) ? val : num;
  }
  for (const intKey of ["grid_cols", "grid_rows", "num_actors", "seed", "max_ticks"]) {
    if (intKey in cfg) cfg[intKey] = Math.round(cfg[intKey]);
  }
  return cfg;
}

function populateConfigForm(config) {
  for (const field of configForm.querySelectorAll("input, select")) {
    const val = config[field.name];
    if (val !== undefined) field.value = val;
  }
}

// ─────────────────────────────────────────────────────────── //
// Event wiring                                               //
// ─────────────────────────────────────────────────────────── //

btnStep.addEventListener("click", async () => {
  stopAutorun();
  render(await postStep());
});

btnAutorun.addEventListener("click", toggleAutorun);

btnReset.addEventListener("click", async () => {
  stopAutorun();
  render(await postReset(readConfigForm()));
});

configForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  stopAutorun();
  render(await postReset(readConfigForm()));
});

speedSlider.addEventListener("input", () => {
  const ms = getIntervalMs();
  speedLabel.textContent = (ms / 1000).toFixed(1) + " s";
  if (autorunTimer !== null) { stopAutorun(); startAutorun(); }
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
    statusText.textContent = "Could not connect — is the server running?";
    statusText.style.color = "var(--danger)";
    console.error(err);
  }
})();
