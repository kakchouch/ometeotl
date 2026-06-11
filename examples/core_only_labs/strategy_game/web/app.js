const territoryCenters = {
  A: { x: 110, y: 85 },
  B: { x: 260, y: 85 },
  C: { x: 410, y: 85 },
  D: { x: 110, y: 235 },
  E: { x: 260, y: 235 },
  F: { x: 410, y: 235 },
};

const statusEl = document.getElementById("status");
const scoreRedEl = document.getElementById("score-red");
const scoreBlueEl = document.getElementById("score-blue");
const actionsEl = document.getElementById("actions");
const logEl = document.getElementById("log");
const redUnit = document.getElementById("red-unit");
const blueUnit = document.getElementById("blue-unit");
const resetBtn = document.getElementById("reset");

let latestState = null;

async function fetchState() {
  const response = await fetch("/api/state");
  if (!response.ok) {
    throw new Error("Unable to fetch state");
  }
  return response.json();
}

async function postJson(url, payload = {}) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Request failed");
  }
  return data;
}

function setUnitPosition(unit, territoryId) {
  const center = territoryCenters[territoryId];
  if (!center) {
    return;
  }
  unit.setAttribute("cx", String(center.x));
  unit.setAttribute("cy", String(center.y));
}

function updateBoard(territories) {
  territories.forEach((territory) => {
    const el = document.querySelector(`.territory[data-id="${territory.id}"]`);
    if (!el) {
      return;
    }
    el.classList.remove("red-owner", "blue-owner");
    if (territory.owner === "player-red") {
      el.classList.add("red-owner");
    } else if (territory.owner === "player-blue") {
      el.classList.add("blue-owner");
    }

    if (territory.red_here === "1") {
      setUnitPosition(redUnit, territory.id);
    }
    if (territory.blue_here === "1") {
      setUnitPosition(blueUnit, territory.id);
    }
  });
}

function renderActions(state) {
  actionsEl.innerHTML = "";

  state.legal_actions.forEach((action) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = action.label;
    button.disabled = state.game_over || state.active_player !== "player-red";

    button.addEventListener("click", async () => {
      button.disabled = true;
      try {
        const next = await postJson("/api/action", {
          action_type: action.action_type,
          target: action.target,
        });
        render(next);
      } catch (error) {
        statusEl.textContent = String(error);
        button.disabled = false;
      }
    });

    actionsEl.appendChild(button);
  });
}

function renderLog(lines) {
  logEl.innerHTML = "";
  lines.slice().reverse().forEach((line) => {
    const item = document.createElement("li");
    item.textContent = line;
    logEl.appendChild(item);
  });
}

function renderStatus(state) {
  if (state.game_over) {
    if (state.winner === "draw") {
      statusEl.textContent = "Game over: draw.";
      return;
    }
    const winner = state.winner === "player-red" ? "Red" : "Blue";
    statusEl.textContent = `Game over: ${winner} wins.`;
    return;
  }

  const active = state.active_player === "player-red" ? "Red" : "Blue";
  statusEl.textContent = `Turn ${state.turn_number}: ${active} to play.`;
}

function render(state) {
  latestState = state;
  scoreRedEl.textContent = state.scores["player-red"];
  scoreBlueEl.textContent = state.scores["player-blue"];
  updateBoard(state.territories);
  renderActions(state);
  renderLog(state.action_log);
  renderStatus(state);
}

async function init() {
  try {
    render(await fetchState());
  } catch (error) {
    statusEl.textContent = String(error);
  }
}

resetBtn.addEventListener("click", async () => {
  try {
    const state = await postJson("/api/reset", {});
    render(state);
  } catch (error) {
    statusEl.textContent = String(error);
  }
});

document.querySelectorAll(".territory").forEach((territory) => {
  territory.addEventListener("click", async () => {
    if (!latestState || latestState.game_over || latestState.active_player !== "player-red") {
      return;
    }

    const id = territory.dataset.id || "";
    const moveAction = latestState.legal_actions.find(
      (action) => action.action_type === "move" && action.target === id
    );

    if (!moveAction) {
      return;
    }

    try {
      const next = await postJson("/api/action", {
        action_type: moveAction.action_type,
        target: moveAction.target,
      });
      render(next);
    } catch (error) {
      statusEl.textContent = String(error);
    }
  });
});

init();
