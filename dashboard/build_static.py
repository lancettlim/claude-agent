"""Static-HTML dashboard prototype for the Pokémon Champions data platform.

M6 tech-stack comparison, Prototype B. Reads data/marts/*.csv, bakes it into
a single self-contained HTML file (no server, no external requests, no
build step at view time), and writes it to dashboard/static/index.html.
Run with:

    uv run python dashboard/build_static.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from game_data import TYPE_CHART, TYPE_COLORS, TYPE_TEXT_COLORS, WEATHER_TERRAIN_ABILITIES

REPO_ROOT = Path(__file__).resolve().parents[1]
MARTS_DIR = REPO_ROOT / "data" / "marts"
OUTPUT_PATH = Path(__file__).resolve().parent / "static" / "index.html"


def _records(df: pd.DataFrame) -> list[dict]:
    return json.loads(df.to_json(orient="records"))


def load_payload() -> dict:
    usage = pd.read_csv(MARTS_DIR / "pokemon_usage_summary.csv")
    win_rate = pd.read_csv(MARTS_DIR / "pokemon_win_rate_summary.csv")
    build = pd.read_csv(MARTS_DIR / "pokemon_build_usage.csv")
    move = pd.read_csv(MARTS_DIR / "pokemon_move_usage.csv")
    core = pd.read_csv(MARTS_DIR / "pokemon_team_core_usage.csv")
    legality = pd.read_csv(MARTS_DIR / "legality_summary_by_regulation.csv")
    stat_delta = pd.read_csv(MARTS_DIR / "stat_change_leaderboard.csv")
    stat_profile = pd.read_csv(MARTS_DIR / "pokemon_stat_profile.csv")
    tera = pd.read_csv(MARTS_DIR / "pokemon_tera_type_usage.csv")
    ability = pd.read_csv(MARTS_DIR / "pokemon_ability_usage.csv")

    pokemon_options = sorted(usage.loc[usage["event_tier"].isna(), "pokemon_key"].unique())

    return {
        "usage": _records(usage),
        "winRate": _records(win_rate),
        "build": _records(build),
        "move": _records(move),
        "core": _records(core),
        "legality": _records(legality),
        "statDelta": _records(stat_delta),
        "statProfile": _records(stat_profile),
        "tera": _records(tera),
        "ability": _records(ability),
        "pokemonOptions": pokemon_options,
        "typeColors": TYPE_COLORS,
        "typeTextColors": TYPE_TEXT_COLORS,
        "typeChart": TYPE_CHART,
        "weatherTerrainAbilities": sorted(WEATHER_TERRAIN_ABILITIES),
    }


HTML_TEMPLATE = """<!doctype html>
<title>Pokémon Champions Dashboard</title>
<meta name="description" content="Static HTML dashboard prototype (Prototype B) for the Pokémon Champions competitive data platform.">
<style>
  :root {
    color-scheme: light;
    --surface-1:      #fcfcfb;
    --page-plane:     #f9f9f7;
    --text-primary:   #0b0b0b;
    --text-secondary: #52514e;
    --text-muted:     #898781;
    --gridline:       #e1e0d9;
    --baseline:       #c3c2b7;
    --border:         rgba(11,11,11,0.10);
    --series-1:       #2a78d6;
    --series-2:       #008300;
    --good:           #006300;
  }
  @media (prefers-color-scheme: dark) {
    :root:where(:not([data-theme="light"])) {
      color-scheme: dark;
      --surface-1:      #1a1a19;
      --page-plane:     #0d0d0d;
      --text-primary:   #ffffff;
      --text-secondary: #c3c2b7;
      --text-muted:     #898781;
      --gridline:       #2c2c2a;
      --baseline:       #383835;
      --border:         rgba(255,255,255,0.10);
      --series-1:       #3987e5;
      --series-2:       #008300;
      --good:           #0ca30c;
    }
  }
  :root[data-theme="dark"] {
    color-scheme: dark;
    --surface-1:      #1a1a19;
    --page-plane:     #0d0d0d;
    --text-primary:   #ffffff;
    --text-secondary: #c3c2b7;
    --text-muted:     #898781;
    --gridline:       #2c2c2a;
    --baseline:       #383835;
    --border:         rgba(255,255,255,0.10);
    --series-1:       #3987e5;
    --series-2:       #008300;
    --good:           #0ca30c;
  }

  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    background: var(--page-plane);
    color: var(--text-primary);
  }
  .viz-root { max-width: 1200px; margin: 0 auto; padding: 24px 20px 64px; }
  h1 { font-size: 1.6rem; margin: 0 0 4px; }
  .subtitle { color: var(--text-secondary); margin: 0 0 24px; font-size: 0.9rem; }

  .kpi-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 12px;
    margin-bottom: 28px;
  }
  .kpi-tile {
    background: var(--surface-1);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px 16px;
  }
  .kpi-label { color: var(--text-secondary); font-size: 0.78rem; margin-bottom: 6px; }
  .kpi-value { font-size: 1.5rem; font-weight: 600; overflow-wrap: anywhere; }
  .kpi-delta { color: var(--good); font-size: 0.82rem; margin-top: 4px; }

  .panel {
    background: var(--surface-1);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px 18px;
    margin-bottom: 20px;
  }
  .panel h2 { font-size: 1.05rem; margin: 0 0 12px; }
  .charts-row { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  @media (max-width: 800px) { .charts-row { grid-template-columns: 1fr; } }

  .filters { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 20px; }
  .filters label { display: flex; flex-direction: column; font-size: 0.8rem; color: var(--text-secondary); gap: 4px; }
  select, input[type="search"] {
    font: inherit;
    padding: 6px 10px;
    border-radius: 6px;
    border: 1px solid var(--border);
    background: var(--surface-1);
    color: var(--text-primary);
  }

  .bar-row { display: flex; align-items: center; gap: 8px; margin: 3px 0; }
  .bar-label { width: 130px; flex-shrink: 0; font-size: 0.78rem; color: var(--text-secondary); text-align: right; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .bar-track { flex: 1; background: var(--gridline); border-radius: 3px; height: 16px; position: relative; }
  .bar-fill { height: 100%; border-radius: 3px; min-width: 2px; }
  .bar-value { font-size: 0.75rem; color: var(--text-muted); width: 56px; flex-shrink: 0; }

  table { border-collapse: collapse; width: 100%; font-size: 0.85rem; }
  th, td { text-align: left; padding: 5px 8px; border-bottom: 1px solid var(--gridline); }
  th { color: var(--text-secondary); font-weight: 600; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.02em; }

  .drilldown-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; margin-top: 12px; }
  .caption { color: var(--text-secondary); font-size: 0.85rem; margin-top: 10px; }

  .type-badge { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 0.7rem; margin-right: 4px; }
  .poke-thumb { width: 28px; height: 28px; object-fit: contain; vertical-align: middle; }
  .hero-image { width: 120px; height: 120px; object-fit: contain; }
  .stat-name { font-weight: 600; font-size: 0.8rem; margin-top: 10px; margin-bottom: 2px; }
  .compare-picker { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 16px; }
  .compare-side { flex: 1; min-width: 220px; text-align: center; }
  .compare-side h3 { margin: 8px 0 4px; }
  .three-col { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 20px; }
  table.sortable th[data-key] { cursor: pointer; user-select: none; }
  table.sortable th[data-key]:hover { color: var(--text-primary); }
  .scroll-table { max-height: 420px; overflow-y: auto; }
</style>

<div class="viz-root">
  <h1>Pokémon Champions Competitive Dashboard</h1>
  <p class="subtitle">Prototype B — static HTML, data baked in at build time. Regenerate with <code>uv run python dashboard/build_static.py</code>.</p>

  <div class="kpi-row" id="kpi-row"></div>

  <div class="filters">
    <label>Tournament tier
      <select id="tier-select"></select>
    </label>
    <label>Regulation
      <select id="regulation-select"></select>
    </label>
  </div>

  <div class="charts-row">
    <div class="panel">
      <h2>Legal-pool size by regulation</h2>
      <div id="legality-chart"></div>
    </div>
    <div class="panel">
      <h2 id="usage-chart-title">Top 15 used Pokémon</h2>
      <div id="usage-chart"></div>
    </div>
  </div>

  <div class="panel">
    <h2>Speed Tier List</h2>
    <p class="caption">Base speed (Champions-format stats — no EVs, nature, or items modeled).</p>
    <div class="scroll-table" id="speed-tier-table"></div>
  </div>

  <div class="panel">
    <h2>Stat Comparison</h2>
    <div class="compare-picker">
      <label>Pokémon A
        <select id="compare-a-select"></select>
      </label>
      <label>Pokémon B
        <select id="compare-b-select"></select>
      </label>
    </div>
    <div class="compare-picker">
      <div class="compare-side" id="compare-a-side"></div>
      <div class="compare-side" id="compare-b-side"></div>
    </div>
    <div id="compare-chart"></div>
    <p class="caption" id="compare-effectiveness"></p>
  </div>

  <div class="panel">
    <h2>Speed Control</h2>
    <div class="three-col">
      <div>
        <h3>Choice Scarf users</h3>
        <div id="scarf-table"></div>
      </div>
      <div>
        <h3>Tailwind setters</h3>
        <div id="tailwind-table"></div>
      </div>
      <div>
        <h3>Trick Room setters</h3>
        <div id="trick-room-table"></div>
      </div>
    </div>
  </div>

  <div class="panel">
    <h2>Weather / Terrain Setters</h2>
    <div class="scroll-table" id="weather-table"></div>
  </div>

  <div class="panel">
    <h2>Meta Tier List</h2>
    <p class="caption">Sorted by usage; click a column header to re-sort. No invented letter grades.</p>
    <div class="scroll-table" id="meta-tier-table"></div>
  </div>

  <div class="panel">
    <h2>Pokémon drill-down</h2>
    <label>Choose a Pokémon
      <select id="pokemon-select"></select>
    </label>
    <div id="drilldown-hero"></div>
    <div class="drilldown-grid">
      <div>
        <h3>Top items/abilities</h3>
        <table><thead><tr><th>Item</th><th>Ability</th><th>Uses</th></tr></thead><tbody id="build-table"></tbody></table>
      </div>
      <div>
        <h3>Top moves</h3>
        <table><thead><tr><th>Move</th><th>Uses</th></tr></thead><tbody id="move-table"></tbody></table>
      </div>
      <div>
        <h3>Top team cores</h3>
        <table><thead><tr><th>Partner</th><th>Uses</th></tr></thead><tbody id="core-table"></tbody></table>
      </div>
      <div>
        <h3>Top Tera types</h3>
        <table><thead><tr><th>Tera type</th><th>Uses</th></tr></thead><tbody id="tera-table"></tbody></table>
      </div>
    </div>
    <p class="caption" id="winrate-caption"></p>
  </div>
</div>

<script>
const DATA = __DATA_JSON__;

const STAT_PROFILE_BY_KEY = new Map(DATA.statProfile.map((r) => [r.pokemon_key, r]));

// Mirrors dashboard/game_data.py's type_effectiveness()/best_type_effectiveness() —
// keep this in sync with that module if the type chart logic ever changes.
function typeEffectiveness(attackType, defType1, defType2) {
  const chart = DATA.typeChart[attackType] || {};
  let factor = chart[defType1] !== undefined ? chart[defType1] : 1;
  if (defType2) {
    factor *= chart[defType2] !== undefined ? chart[defType2] : 1;
  }
  return factor;
}

function bestTypeEffectiveness(atk1, atk2, def1, def2) {
  let best = typeEffectiveness(atk1, def1, def2);
  if (atk2) {
    best = Math.max(best, typeEffectiveness(atk2, def1, def2));
  }
  return best;
}

function typeBadgeHtml(typeName) {
  if (!typeName) return "";
  const bg = DATA.typeColors[typeName] || "#888888";
  const fg = DATA.typeTextColors[typeName] || "#ffffff";
  return `<span class="type-badge" style="background:${bg};color:${fg}">${typeName}</span>`;
}

function typeBadgesHtml(type1, type2) {
  return typeBadgeHtml(type1) + typeBadgeHtml(type2);
}

function imgCellHtml(url) {
  if (!url) return "";
  return `<img src="${url}" class="poke-thumb" onerror="this.style.display='none'" alt="">`;
}

function el(tag, attrs, children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === "text") node.textContent = v;
    else node.setAttribute(k, v);
  }
  for (const child of children || []) node.appendChild(child);
  return node;
}

function renderBarChart(container, rows, labelKey, valueKey, color) {
  container.innerHTML = "";
  const max = Math.max(...rows.map((r) => r[valueKey]), 1);
  for (const row of rows) {
    const pct = (row[valueKey] / max) * 100;
    const fill = el("div", { class: "bar-fill", style: `width:${pct}%; background:${color}` });
    const track = el("div", { class: "bar-track" }, [fill]);
    const barRow = el("div", { class: "bar-row" }, [
      el("div", { class: "bar-label", text: row[labelKey], title: row[labelKey] }),
      track,
      el("div", { class: "bar-value", text: row[valueKey].toLocaleString() }),
    ]);
    container.appendChild(barRow);
  }
}

function renderSortableTable(container, rows, columns, initialSortKey, initialDir) {
  let sortKey = initialSortKey;
  let sortDir = initialDir || "desc";

  function sortedRows() {
    const copy = [...rows];
    copy.sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (av === bv) return 0;
      const cmp = av > bv ? 1 : -1;
      return sortDir === "asc" ? cmp : -cmp;
    });
    return copy;
  }

  function render() {
    const theadCells = columns
      .map((c) => {
        const arrow = c.key === sortKey ? (sortDir === "asc" ? " ▲" : " ▼") : "";
        return `<th data-key="${c.key}">${c.label}${arrow}</th>`;
      })
      .join("");
    const bodyRows = sortedRows()
      .map(
        (r) =>
          `<tr>${columns.map((c) => `<td>${c.render ? c.render(r) : (r[c.key] ?? "—")}</td>`).join("")}</tr>`
      )
      .join("");
    container.innerHTML = `<table class="sortable"><thead><tr>${theadCells}</tr></thead><tbody>${bodyRows}</tbody></table>`;
    container.querySelectorAll("th[data-key]").forEach((th) => {
      th.addEventListener("click", () => {
        const key = th.dataset.key;
        if (key === sortKey) {
          sortDir = sortDir === "asc" ? "desc" : "asc";
        } else {
          sortKey = key;
          sortDir = "desc";
        }
        render();
      });
    });
  }

  render();
}

function typesDisplayHtml(row) {
  if (!row) return "";
  return typeBadgesHtml(row.type_1, row.type_2);
}

function renderKpis() {
  const regulation = document.getElementById("regulation-select").value;
  const legalRow = DATA.legality.find((r) => r.regulation_code === regulation);
  const overall = DATA.usage.filter((r) => r.event_tier === null);
  const topUsed = [...overall].sort((a, b) => b.usage_count - a.usage_count)[0];
  const topWinRate = [...DATA.winRate].sort((a, b) => b.win_rate - a.win_rate)[0];
  const gainers = DATA.statDelta.filter((r) => r.direction === "gainer");
  const topGainer = gainers.sort((a, b) => a.rank_within_direction - b.rank_within_direction)[0];

  const tiles = [
    ["Legal Pokémon (" + regulation + ")", legalRow ? legalRow.legal_pokemon_count : "—", null],
    ["Most-used Pokémon", topUsed.pokemon_key, topUsed.usage_count.toLocaleString() + " uses"],
    ["Highest win rate", topWinRate.pokemon_key, (topWinRate.win_rate * 100).toFixed(1) + "%"],
    ["Top stat gainer", topGainer.pokemon_key, (topGainer.stat_total_delta >= 0 ? "+" : "") + topGainer.stat_total_delta],
  ];

  const row = document.getElementById("kpi-row");
  row.innerHTML = "";
  for (const [label, value, delta] of tiles) {
    const children = [
      el("div", { class: "kpi-label", text: label }),
      el("div", { class: "kpi-value", text: String(value) }),
    ];
    if (delta) children.push(el("div", { class: "kpi-delta", text: delta }));
    row.appendChild(el("div", { class: "kpi-tile" }, children));
  }
}

function renderLegalityChart() {
  renderBarChart(
    document.getElementById("legality-chart"),
    DATA.legality,
    "regulation_code",
    "legal_pokemon_count",
    "var(--series-1)"
  );
}

function renderUsageChart() {
  const tier = document.getElementById("tier-select").value;
  const rows = DATA.usage.filter((r) => (tier === "All" ? r.event_tier === null : r.event_tier === tier));
  const top15 = [...rows].sort((a, b) => b.usage_count - a.usage_count).slice(0, 15);
  document.getElementById("usage-chart-title").textContent = `Top 15 used Pokémon (${tier})`;
  renderBarChart(document.getElementById("usage-chart"), top15, "pokemon_key", "usage_count", "var(--series-1)");
}

function renderDrilldown() {
  const pokemon = document.getElementById("pokemon-select").value;

  const profile = STAT_PROFILE_BY_KEY.get(pokemon);
  const hero = document.getElementById("drilldown-hero");
  if (profile) {
    hero.innerHTML = `
      ${profile.image_url ? `<img src="${profile.image_url}" class="hero-image" onerror="this.style.display='none'" alt="">` : ""}
      <div><strong>${pokemon}</strong></div>
      <div>${typesDisplayHtml(profile)}</div>
      <div class="caption">HP ${profile.hp} · Atk ${profile.attack} · Def ${profile.defense} · SpA ${profile.sp_attack} · SpD ${profile.sp_defense} · Spe ${profile.speed} · BST ${profile.stat_total}</div>
    `;
  } else {
    hero.innerHTML = "";
  }

  const buildRows = DATA.build.filter((r) => r.pokemon_key === pokemon).slice(0, 8);
  document.getElementById("build-table").innerHTML = buildRows
    .map((r) => `<tr><td>${r.item_name ?? "—"}</td><td>${r.ability ?? "—"}</td><td>${r.usage_count}</td></tr>`)
    .join("");

  const moveRows = DATA.move.filter((r) => r.pokemon_key === pokemon).slice(0, 8);
  document.getElementById("move-table").innerHTML = moveRows
    .map((r) => `<tr><td>${r.move_name}</td><td>${r.usage_count}</td></tr>`)
    .join("");

  const coreRows = DATA.core
    .filter((r) => r.pokemon_key_a === pokemon || r.pokemon_key_b === pokemon)
    .sort((a, b) => b.usage_count - a.usage_count)
    .slice(0, 8)
    .map((r) => ({ partner: r.pokemon_key_a === pokemon ? r.pokemon_key_b : r.pokemon_key_a, usage_count: r.usage_count }));
  document.getElementById("core-table").innerHTML = coreRows
    .map((r) => `<tr><td>${r.partner}</td><td>${r.usage_count}</td></tr>`)
    .join("");

  const teraRows = DATA.tera.filter((r) => r.pokemon_key === pokemon).slice(0, 8);
  document.getElementById("tera-table").innerHTML = teraRows
    .map((r) => `<tr><td>${r.tera_type}</td><td>${r.usage_count}</td></tr>`)
    .join("");

  const wr = DATA.winRate.find((r) => r.pokemon_key === pokemon);
  const caption = document.getElementById("winrate-caption");
  caption.textContent = wr
    ? `Win-rate proxy: ${(wr.win_rate * 100).toFixed(1)}% (${wr.total_wins}W-${wr.total_losses}L across ${wr.record_count} recorded teams)`
    : "No win-rate proxy data recorded for this Pokémon.";
}

function renderSpeedTierList() {
  const rows = [...DATA.statProfile].sort((a, b) => b.speed - a.speed);
  renderSortableTable(
    document.getElementById("speed-tier-table"),
    rows,
    [
      { key: "image_url", label: "", render: (r) => imgCellHtml(r.image_url) },
      { key: "pokemon_key", label: "Pokémon" },
      { key: "type_1", label: "Type(s)", render: (r) => typesDisplayHtml(r) },
      { key: "speed", label: "Speed" },
      { key: "stat_total", label: "BST" },
    ],
    "speed"
  );
}

function renderStatComparisonChart(rowA, rowB, nameA, nameB) {
  const stats = ["hp", "attack", "defense", "sp_attack", "sp_defense", "speed"];
  const statLabels = { hp: "HP", attack: "Atk", defense: "Def", sp_attack: "SpA", sp_defense: "SpD", speed: "Spe" };
  const max = Math.max(...stats.map((s) => Math.max(rowA[s], rowB[s])), 1);
  const container = document.getElementById("compare-chart");
  container.innerHTML = "";
  for (const s of stats) {
    const wrap = el("div", {});
    wrap.appendChild(el("div", { class: "stat-name", text: statLabels[s] }));
    const pctA = (rowA[s] / max) * 100;
    const pctB = (rowB[s] / max) * 100;
    wrap.appendChild(
      el("div", { class: "bar-row" }, [
        el("div", { class: "bar-label", text: nameA, title: nameA }),
        el("div", { class: "bar-track" }, [
          el("div", { class: "bar-fill", style: `width:${pctA}%; background:var(--series-1)` }),
        ]),
        el("div", { class: "bar-value", text: String(rowA[s]) }),
      ])
    );
    wrap.appendChild(
      el("div", { class: "bar-row" }, [
        el("div", { class: "bar-label", text: nameB, title: nameB }),
        el("div", { class: "bar-track" }, [
          el("div", { class: "bar-fill", style: `width:${pctB}%; background:var(--series-2)` }),
        ]),
        el("div", { class: "bar-value", text: String(rowB[s]) }),
      ])
    );
    container.appendChild(wrap);
  }
}

function renderStatComparison() {
  const pokemonA = document.getElementById("compare-a-select").value;
  const pokemonB = document.getElementById("compare-b-select").value;
  const rowA = STAT_PROFILE_BY_KEY.get(pokemonA);
  const rowB = STAT_PROFILE_BY_KEY.get(pokemonB);
  if (!rowA || !rowB) return;

  document.getElementById("compare-a-side").innerHTML = `
    ${rowA.image_url ? `<img src="${rowA.image_url}" class="hero-image" onerror="this.style.display='none'" alt="">` : ""}
    <h3>${pokemonA}</h3>
    <div>${typesDisplayHtml(rowA)}</div>
  `;
  document.getElementById("compare-b-side").innerHTML = `
    ${rowB.image_url ? `<img src="${rowB.image_url}" class="hero-image" onerror="this.style.display='none'" alt="">` : ""}
    <h3>${pokemonB}</h3>
    <div>${typesDisplayHtml(rowB)}</div>
  `;

  renderStatComparisonChart(rowA, rowB, pokemonA, pokemonB);

  const effAtoB = bestTypeEffectiveness(rowA.type_1, rowA.type_2, rowB.type_1, rowB.type_2);
  const effBtoA = bestTypeEffectiveness(rowB.type_1, rowB.type_2, rowA.type_1, rowA.type_2);
  document.getElementById("compare-effectiveness").textContent =
    `${pokemonA}'s types are ${effAtoB}× effective against ${pokemonB}. ` +
    `${pokemonB}'s types are ${effBtoA}× effective against ${pokemonA}.`;
}

function renderSpeedControl() {
  const withImage = (rows) =>
    rows.map((r) => ({ ...r, image_url: (STAT_PROFILE_BY_KEY.get(r.pokemon_key) || {}).image_url }));
  const columns = [
    { key: "image_url", label: "", render: (r) => imgCellHtml(r.image_url) },
    { key: "pokemon_key", label: "Pokémon" },
    { key: "usage_count", label: "Uses" },
  ];

  renderSortableTable(
    document.getElementById("scarf-table"),
    withImage(DATA.build.filter((r) => r.item_name === "Choice Scarf")),
    columns,
    "usage_count"
  );
  renderSortableTable(
    document.getElementById("tailwind-table"),
    withImage(DATA.move.filter((r) => r.move_name === "Tailwind")),
    columns,
    "usage_count"
  );
  renderSortableTable(
    document.getElementById("trick-room-table"),
    withImage(DATA.move.filter((r) => r.move_name === "Trick Room")),
    columns,
    "usage_count"
  );
}

function renderWeatherTerrain() {
  const rows = DATA.ability
    .filter((r) => DATA.weatherTerrainAbilities.includes(r.ability))
    .map((r) => ({ ...r, image_url: (STAT_PROFILE_BY_KEY.get(r.pokemon_key) || {}).image_url }));
  renderSortableTable(
    document.getElementById("weather-table"),
    rows,
    [
      { key: "image_url", label: "", render: (r) => imgCellHtml(r.image_url) },
      { key: "pokemon_key", label: "Pokémon" },
      { key: "ability", label: "Ability" },
      { key: "usage_count", label: "Uses" },
    ],
    "usage_count"
  );
}

function renderMetaTierList() {
  const winRateByKey = new Map(DATA.winRate.map((r) => [r.pokemon_key, r]));
  const overall = DATA.usage.filter((r) => r.event_tier === null);
  const rows = overall.map((r) => {
    const wr = winRateByKey.get(r.pokemon_key);
    const profile = STAT_PROFILE_BY_KEY.get(r.pokemon_key);
    return {
      ...r,
      image_url: profile ? profile.image_url : null,
      type_1: profile ? profile.type_1 : null,
      type_2: profile ? profile.type_2 : null,
      win_rate: wr ? wr.win_rate : null,
      record_count: wr ? wr.record_count : null,
    };
  });
  renderSortableTable(
    document.getElementById("meta-tier-table"),
    rows,
    [
      { key: "image_url", label: "", render: (r) => imgCellHtml(r.image_url) },
      { key: "pokemon_key", label: "Pokémon" },
      { key: "type_1", label: "Type(s)", render: (r) => typesDisplayHtml(r) },
      { key: "usage_rank", label: "Usage Rank" },
      { key: "usage_count", label: "Uses" },
      { key: "win_rate", label: "Win Rate", render: (r) => (r.win_rate != null ? `${(r.win_rate * 100).toFixed(1)}%` : "—") },
      { key: "record_count", label: "Recorded Teams" },
    ],
    "usage_rank",
    "asc"
  );
}

function populateSelect(select, options) {
  select.innerHTML = options.map((o) => `<option value="${o}">${o}</option>`).join("");
}

const tierSelect = document.getElementById("tier-select");
const regulationSelect = document.getElementById("regulation-select");
const pokemonSelect = document.getElementById("pokemon-select");
const compareASelect = document.getElementById("compare-a-select");
const compareBSelect = document.getElementById("compare-b-select");

const tiers = [...new Set(DATA.usage.map((r) => r.event_tier).filter((t) => t !== null))].sort();
populateSelect(tierSelect, ["All", ...tiers]);
populateSelect(regulationSelect, DATA.legality.map((r) => r.regulation_code).sort());
populateSelect(pokemonSelect, DATA.pokemonOptions);
populateSelect(compareASelect, DATA.pokemonOptions);
populateSelect(compareBSelect, DATA.pokemonOptions);
if (DATA.pokemonOptions.length > 1) compareBSelect.value = DATA.pokemonOptions[1];

tierSelect.addEventListener("change", () => { renderUsageChart(); });
regulationSelect.addEventListener("change", () => { renderKpis(); });
pokemonSelect.addEventListener("change", () => { renderDrilldown(); });
compareASelect.addEventListener("change", () => { renderStatComparison(); });
compareBSelect.addEventListener("change", () => { renderStatComparison(); });

renderKpis();
renderLegalityChart();
renderUsageChart();
renderSpeedTierList();
renderStatComparison();
renderSpeedControl();
renderWeatherTerrain();
renderMetaTierList();
renderDrilldown();
</script>
"""


def build() -> None:
    payload = load_payload()
    html = HTML_TEMPLATE.replace("__DATA_JSON__", json.dumps(payload))
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size / 1024:.0f} KiB)")


if __name__ == "__main__":
    build()
