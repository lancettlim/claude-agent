/* Plain vanilla JS — no bundler, no framework, no charting library. Reads
 * window.DASHBOARD_DATA (baked into index.html by pipelines/dashboard/
 * build.py) and wires up the tabs/filters/tables/grids declared in
 * index.html.jinja.
 *
 * This file owns the core framework (tabs, tables, the shared .grid-6xn
 * component) plus the Overview/Usage/Pokémon Profile/Speed Tiers tabs, and
 * exposes shared state/helpers on window.DashboardApp so matchup.js
 * (Matchup tab) and teams.js (Team Builder + Top Teams tabs) — loaded
 * right after this file — can reuse them instead of duplicating. See
 * docs/design-system.md for the full component/token reference.
 *
 * Ranked/grid visuals (see renderGrid6xn/renderRankedList) are plain
 * DOM/CSS, not canvas charts — this dashboard has no Chart.js/CDN
 * dependency. */
(function () {
  "use strict";

  var DATA = window.DASHBOARD_DATA || {
    marts: {},
    kpis: {},
    sprites: {},
    type_icons: {},
    item_icons: {},
    reference_teams: [],
    pokemon_names: {},
  };
  var marts = DATA.marts || {};
  var sprites = DATA.sprites || {};
  var typeIcons = DATA.type_icons || {};
  var itemIcons = DATA.item_icons || {};
  var pokemonNames = DATA.pokemon_names || {};

  // Icon-size tokens (docs/design-system.md's "Icon size scale") — mirrors
  // the --icon-sm/md/lg/xl CSS custom properties in index.html.jinja.
  var ICON_SIZES = { sm: 40, md: 64, lg: 96, xl: 128 };

  var ALL_TYPES = [
    "normal", "fire", "water", "electric", "grass", "ice", "fighting",
    "poison", "ground", "flying", "psychic", "bug", "rock", "ghost",
    "dragon", "dark", "steel", "fairy",
  ];

  // ---------- generic helpers ----------

  function escapeHtml(value) {
    var map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
    return String(value).replace(/[&<>"']/g, function (c) {
      return map[c];
    });
  }

  // Alphabetical distinct-values helper, used only for non-Pokémon selects
  // (e.g. tournament tier) where alphabetical is still the more findable
  // order — Pokémon pickers use distinctSortedByMetric instead (see below;
  // docs/design-system.md's ordering convention no longer has an
  // alphabetical exception for Pokémon-name dropdowns).
  function distinctSorted(rows, field) {
    var seen = {};
    var out = [];
    rows.forEach(function (row) {
      var value = row[field];
      if (value && !seen[value]) {
        seen[value] = true;
        out.push(value);
      }
    });
    out.sort();
    return out;
  }

  // Distinct pokemon_name values from rows, ordered by descending
  // usage_share (metricByKey: pokemon_key -> usage_share) rather than
  // alphabetically — every Pokémon-picker dropdown uses this now.
  function distinctSortedByMetric(rows, metricByKey) {
    var seen = {};
    var out = [];
    rows.forEach(function (row) {
      var name = row.pokemon_name;
      if (name && !seen[name]) {
        seen[name] = true;
        out.push({ name: name, key: row.pokemon_key });
      }
    });
    out.sort(function (a, b) {
      return (metricByKey[b.key] || 0) - (metricByKey[a.key] || 0);
    });
    return out.map(function (o) {
      return o.name;
    });
  }

  function usageShareByKey() {
    var lookup = {};
    (marts.pokemon_usage_summary || []).forEach(function (r) {
      if (!r.event_tier) lookup[r.pokemon_key] = r.usage_share || 0;
    });
    return lookup;
  }

  // pokemon_key -> its pokemon_champions_profile row (stats, type_1/type_2,
  // usage/win-rate) — the shared join point for the Usage/Speed
  // Tiers/Matchup tabs' type and stat-range filters.
  function championsProfileByKey() {
    var lookup = {};
    (marts.pokemon_champions_profile || []).forEach(function (r) {
      lookup[r.pokemon_key] = r;
    });
    return lookup;
  }

  // Rough physical/special/mixed role per Pokémon, derived from the
  // damage-category split of its own recorded moveset (pokemon_move_usage,
  // weighted by usage_count) — not a sourced attribute, a UX bucketing
  // convention like SPEED_TIERS below. Status-only moves don't count
  // toward either side.
  function roleByKey() {
    var counts = {};
    (marts.pokemon_move_usage || []).forEach(function (r) {
      if (r.category !== "physical" && r.category !== "special") return;
      var c = counts[r.pokemon_key] || (counts[r.pokemon_key] = { physical: 0, special: 0 });
      c[r.category] += r.usage_count || 1;
    });
    var roles = {};
    Object.keys(counts).forEach(function (key) {
      var c = counts[key];
      if (c.physical === 0 && c.special === 0) return;
      if (c.physical > c.special * 1.5) roles[key] = "physical";
      else if (c.special > c.physical * 1.5) roles[key] = "special";
      else roles[key] = "mixed";
    });
    return roles;
  }

  function fillSelect(select, options, allLabel) {
    select.innerHTML = "";
    var allOption = document.createElement("option");
    allOption.value = "";
    allOption.textContent = allLabel;
    select.appendChild(allOption);
    options.forEach(function (value) {
      var opt = document.createElement("option");
      opt.value = value;
      opt.textContent = value;
      select.appendChild(opt);
    });
  }

  function renderRows(tbody, rows, rowHtmlFn) {
    tbody.innerHTML = "";
    rows.forEach(function (row, index) {
      var tr = document.createElement("tr");
      tr.innerHTML = rowHtmlFn(row, index);
      tbody.appendChild(tr);
    });
  }

  // Numeric min/max <input type="number"> pair filter (docs/design-system.md's
  // "range-filter" component) — used for usage %/win rate/speed/stat
  // ranges. Empty min/max means unbounded on that side; a null/undefined
  // value fails the filter as soon as either bound is set.
  function inRange(value, minEl, maxEl) {
    var hasMin = minEl && minEl.value !== "";
    var hasMax = maxEl && maxEl.value !== "";
    if (!hasMin && !hasMax) return true;
    if (value === null || value === undefined) return false;
    if (hasMin && value < parseFloat(minEl.value)) return false;
    if (hasMax && value > parseFloat(maxEl.value)) return false;
    return true;
  }

  // Multi-select type filter, rendered as a row of toggle chips (one per
  // ALL_TYPES entry). `selected` is a plain {type_name: true} map the
  // caller owns; an empty map means "no filter, show everything".
  function renderTypeFilterChips(container, selected, onChange) {
    if (!container) return;
    container.innerHTML = "";
    ALL_TYPES.forEach(function (type) {
      var chip = document.createElement("button");
      chip.type = "button";
      chip.className = "toggle-chip";
      chip.setAttribute("aria-pressed", selected[type] ? "true" : "false");
      chip.innerHTML = typeIconImg(type, 14) + " " + type;
      chip.addEventListener("click", function () {
        if (selected[type]) {
          delete selected[type];
        } else {
          selected[type] = true;
        }
        chip.setAttribute("aria-pressed", selected[type] ? "true" : "false");
        onChange();
      });
      container.appendChild(chip);
    });
  }

  function hasAnySelectedType(selected) {
    for (var key in selected) {
      if (Object.prototype.hasOwnProperty.call(selected, key)) return true;
    }
    return false;
  }

  function passesTypeFilter(selected, type1, type2) {
    if (!hasAnySelectedType(selected)) return true;
    return !!(selected[type1] || (type2 && selected[type2]));
  }

  // A single select-driven drill-down: fills the select from the distinct
  // pokemon_name values across rows (ranked by usage relevance, not
  // alphabetically), defaults to the first option, and calls
  // render(selectedValue) on load and on every change.
  function setupDrilldown(opts) {
    var select = document.getElementById(opts.selectId);
    if (!select) return;
    var metricByKey = usageShareByKey();
    var options = distinctSortedByMetric(opts.rows, metricByKey);
    fillSelect(select, options, opts.allLabel || "Select a Pokémon…");
    select.addEventListener("change", function () {
      opts.render(select.value);
    });
    if (options.length) {
      select.value = options[0];
    }
    opts.render(select.value);
  }

  // ---------- sprite/icon cell rendering ----------

  function spriteImg(pokemonKey, sizePx) {
    var src = sprites[pokemonKey];
    if (!src) return "";
    var size = sizePx || ICON_SIZES.sm;
    return (
      '<img class="cell-icon" style="width:' + size + "px;height:" + size + 'px" src="' +
      src + '" alt="">'
    );
  }

  function pokemonCell(pokemonKey, pokemonName) {
    return (
      '<div class="cell-with-icon">' + spriteImg(pokemonKey) + "<span>" +
      escapeHtml(pokemonName) + "</span></div>"
    );
  }

  // The committed type-icon PNGs (static/icons/types/) are wide 200x40
  // "icon + type name" badges (a PokéAPI/sprites generation-ix asset), not
  // bare square icons — the symbol always sits in a fixed-width square on
  // the left edge, with the type name filling the rest. Squishing the
  // whole 5:1 image into a square (the old approach) stretched the text
  // into an illegible blob; instead this crops to just that left square
  // (an overflow:hidden window sized to `size`, holding a height:`size`
  // image scaled to its natural ~5:1 aspect so only the icon shows) —
  // a real icon-only emblem, not a squished text badge.
  function typeIconImg(typeName, sizePx) {
    var src = typeIcons[typeName];
    if (!src) return "";
    var size = sizePx || 18;
    return (
      '<span class="type-icon-crop" style="width:' + size + "px;height:" + size +
      'px" title="' + escapeHtml(typeName) + '">' +
      '<img src="' + src + '" alt="' + escapeHtml(typeName) + '" style="height:' + size + 'px">' +
      "</span>"
    );
  }

  // Renders a Pokémon's type_1/type_2 into `container` as a type-badge row
  // of icon-only emblems (no visible text label — the type name is exposed
  // via each pill's aria-label and the icon's title attribute instead).
  // large=true switches to the Profile header's --icon-xl dual-type
  // display (docs/design-system.md's "Larger type badge"); otherwise it's
  // the compact pill used in the Matchup tab's picker panels.
  function renderTypeBadgeRow(container, type1, type2, large) {
    if (!container) return;
    var types = [type1, type2].filter(Boolean);
    if (!types.length) {
      container.innerHTML = "";
      return;
    }
    if (large) {
      container.className = "type-badge-row type-badge-lg";
      container.innerHTML = types
        .map(function (t) {
          return '<div class="type-pill-lg" role="img" aria-label="' + escapeHtml(t) + ' type">' +
            typeIconImg(t, ICON_SIZES.xl) + "</div>";
        })
        .join("");
    } else {
      container.className = "type-badge-row";
      container.innerHTML = types
        .map(function (t) {
          return '<span class="type-pill" role="img" aria-label="' + escapeHtml(t) + ' type">' +
            typeIconImg(t, 18) + "</span>";
        })
        .join("");
    }
  }

  function formatPercent(value) {
    return value === null || value === undefined ? "—" : (value * 100).toFixed(1) + "%";
  }

  // Speed-tier bucketing (docs/design-system.md's "Speed-tier badge"
  // component) — thresholds are documented there and must stay in sync
  // with this function, the single source of truth for the bucketing
  // logic itself.
  var SPEED_TIERS = [
    { max: Infinity, min: 120, label: "Blazing", cls: "badge-speed-blazing" },
    { max: 119, min: 90, label: "Fast", cls: "badge-speed-fast" },
    { max: 89, min: 60, label: "Average", cls: "badge-speed-average" },
    { max: 59, min: -Infinity, label: "Slow", cls: "badge-speed-slow" },
  ];
  function speedTier(speed) {
    for (var i = 0; i < SPEED_TIERS.length; i++) {
      if (speed >= SPEED_TIERS[i].min) return SPEED_TIERS[i];
    }
    return SPEED_TIERS[SPEED_TIERS.length - 1];
  }
  function speedTierBadge(speed) {
    var tier = speedTier(speed);
    return '<span class="badge ' + tier.cls + '">' + tier.label + "</span>";
  }

  function itemCell(itemName) {
    if (!itemName) return "—";
    var src = itemIcons[itemName];
    var icon = src ? '<img class="cell-icon" src="' + src + '" alt="">' : "";
    return '<div class="cell-with-icon">' + icon + "<span>" + escapeHtml(itemName) + "</span></div>";
  }

  // ---------- 6-wide grid (docs/design-system.md's ".grid-6xn component") ----------

  // The dashboard's primary visual for any usage/win-rate metric,
  // replacing the old per-metric ranked-list bars (dashboard "replace
  // usage/win-rate bar charts with a 6xn grid just like overview" ask).
  // opts mirror renderRankedList's: keyFn/iconFn, labelFn, displayFn
  // (bolded headline value), subFn (optional second line — a description,
  // a secondary stat), showRank (default true).
  function renderGrid6xn(container, rows, opts) {
    if (!container) return;
    container.innerHTML = "";
    if (!rows.length) {
      container.innerHTML = '<p class="empty-state">No data yet.</p>';
      return;
    }
    rows.forEach(function (row, i) {
      var iconSrc = opts.iconFn ? opts.iconFn(row) : opts.keyFn ? sprites[opts.keyFn(row)] : null;
      var tile = document.createElement("div");
      tile.className = "grid-6xn-tile" + (i === 0 && opts.showLeader !== false ? " is-leader" : "");
      tile.innerHTML =
        (opts.showRank !== false ? '<span class="badge badge-rank">#' + (i + 1) + "</span>" : "") +
        (iconSrc ? '<img src="' + iconSrc + '" alt="">' : "") +
        '<div class="grid-6xn-label">' + escapeHtml(opts.labelFn(row)) + "</div>" +
        '<div class="grid-6xn-value">' + escapeHtml(opts.displayFn(row)) + "</div>" +
        (opts.subFn && opts.subFn(row) ? '<div class="grid-6xn-sub">' + escapeHtml(opts.subFn(row)) + "</div>" : "");
      container.appendChild(tile);
    });
  }

  // ---------- sortable table ----------

  // Wraps a <table> whose <th data-sort-key> headers should re-sort its
  // body on click (toggling asc/desc), replacing the previous fixed-sort-
  // only tables. Renders once immediately; call .setRows(newRows) when the
  // underlying data changes (e.g. a filter) to re-render with the current
  // sort state preserved.
  function makeSortableTable(table, initialRows, renderRowFn, opts) {
    opts = opts || {};
    var tbody = table.querySelector("tbody");
    var ths = table.querySelectorAll("th[data-sort-key]");
    var state = { key: opts.defaultKey || null, dir: opts.defaultDir || "desc" };
    var rows = initialRows;

    function sortedRows() {
      if (!state.key) return rows;
      return rows.slice().sort(function (a, b) {
        var av = a[state.key];
        var bv = b[state.key];
        av = av === null || av === undefined ? -Infinity : av;
        bv = bv === null || bv === undefined ? -Infinity : bv;
        var cmp = av < bv ? -1 : av > bv ? 1 : 0;
        return state.dir === "asc" ? cmp : -cmp;
      });
    }

    function render() {
      renderRows(tbody, sortedRows(), renderRowFn);
      ths.forEach(function (th) {
        var existing = th.querySelector(".sort-indicator");
        if (existing) existing.remove();
        if (th.getAttribute("data-sort-key") === state.key) {
          var span = document.createElement("span");
          span.className = "sort-indicator";
          span.textContent = state.dir === "asc" ? "▲" : "▼";
          th.appendChild(span);
        }
      });
    }

    ths.forEach(function (th) {
      th.addEventListener("click", function () {
        var key = th.getAttribute("data-sort-key");
        if (state.key === key) {
          state.dir = state.dir === "desc" ? "asc" : "desc";
        } else {
          state.key = key;
          state.dir = "desc";
        }
        render();
      });
    });

    render();
    return {
      setRows: function (newRows) {
        rows = newRows;
        render();
      },
    };
  }

  // ---------- tab switching ----------

  var tabInitializers = {};
  var initialized = {};

  function registerTab(tabId, initFn) {
    tabInitializers[tabId] = initFn;
  }

  function setupTabs(onActivate) {
    var buttons = document.querySelectorAll(".tab-btn");
    var panels = document.querySelectorAll(".tab-panel");
    function activate(tabId) {
      buttons.forEach(function (btn) {
        btn.setAttribute("aria-selected", btn.getAttribute("data-tab") === tabId ? "true" : "false");
      });
      panels.forEach(function (panel) {
        panel.hidden = panel.getAttribute("data-panel") !== tabId;
      });
      if (onActivate) onActivate(tabId);
    }
    buttons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        activate(btn.getAttribute("data-tab"));
      });
    });
    activate("overview");
  }

  // ---------- sub-tabs ----------

  // A pill row nested inside one top-level tab/section (docs/design-
  // system.md's "Sub-tabs" component) — e.g. Usage's Usage-leaders/Win-
  // rate-leaders, Pokémon Profile's Items/Ability/Moves/Team Cores.
  // buttons/panels are NodeLists or arrays; buttons carry data-subtab,
  // panels carry data-subpanel, matched by that id. Defaults to the first
  // button. Distinct from setupTabs (the page's seven top-level tabs).
  function setupSubTabs(buttons, panels, onActivate) {
    buttons = Array.prototype.slice.call(buttons);
    panels = Array.prototype.slice.call(panels);
    function activate(id) {
      buttons.forEach(function (btn) {
        btn.setAttribute("aria-selected", btn.getAttribute("data-subtab") === id ? "true" : "false");
      });
      panels.forEach(function (panel) {
        panel.hidden = panel.getAttribute("data-subpanel") !== id;
      });
      if (onActivate) onActivate(id);
    }
    buttons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        activate(btn.getAttribute("data-subtab"));
      });
    });
    if (buttons.length) activate(buttons[0].getAttribute("data-subtab"));
  }

  // ---------- per-tab setup (each called once, on first activation) ----------

  function setupOverview() {
    var top12 = (DATA.kpis && DATA.kpis.top_12_pokemon) || [];
    renderGrid6xn(document.getElementById("overview-top-12"), top12, {
      keyFn: function (r) {
        return r.pokemon_key;
      },
      labelFn: function (r) {
        return r.pokemon_name;
      },
      displayFn: function (r) {
        return formatPercent(r.usage_share);
      },
      subFn: function (r) {
        return formatPercent(r.win_rate) + " win rate";
      },
    });
  }

  function setupUsage() {
    var usageRows = marts.pokemon_usage_summary || [];
    var profileByKey = championsProfileByKey();
    var roles = roleByKey();

    var tierSelect = document.getElementById("usage-tier-filter");
    var roleSelect = document.getElementById("usage-role-filter");
    var typeFilterEl = document.getElementById("usage-type-filter");
    var shareMin = document.getElementById("usage-share-min");
    var shareMax = document.getElementById("usage-share-max");
    var speedMin = document.getElementById("usage-speed-min");
    var speedMax = document.getElementById("usage-speed-max");
    var selectedTypes = {};

    function filteredRows(tier) {
      return usageRows.filter(function (r) {
        if ((r.event_tier || "") !== tier) return false;
        var profile = profileByKey[r.pokemon_key];
        if (!passesTypeFilter(selectedTypes, profile && profile.type_1, profile && profile.type_2)) return false;
        if (roleSelect && roleSelect.value && roles[r.pokemon_key] !== roleSelect.value) return false;
        if (!inRange(r.usage_share != null ? r.usage_share * 100 : null, shareMin, shareMax)) return false;
        if (!inRange(profile ? profile.speed : null, speedMin, speedMax)) return false;
        return true;
      });
    }

    var grid = document.getElementById("usage-grid");
    var usageTable = document.getElementById("usage-leaders-table");
    var usageTableSortable = usageTable
      ? makeSortableTable(
          usageTable,
          [],
          function (r) {
            return (
              '<td><span class="badge badge-rank">#' + r.usage_rank + "</span></td>" +
              "<td>" + pokemonCell(r.pokemon_key, r.pokemon_name) + "</td>" +
              "<td>" + formatPercent(r.usage_share) + "</td>"
            );
          },
          {}
        )
      : null;

    function drawUsage() {
      var tier = tierSelect ? tierSelect.value : "";
      var rows = filteredRows(tier)
        .slice()
        .sort(function (a, b) {
          return a.usage_rank - b.usage_rank;
        });
      renderGrid6xn(grid, rows.slice(0, 18), {
        keyFn: function (r) {
          return r.pokemon_key;
        },
        labelFn: function (r) {
          return r.pokemon_name;
        },
        displayFn: function (r) {
          return formatPercent(r.usage_share);
        },
      });
      if (usageTableSortable) usageTableSortable.setRows(rows.slice(0, 30));
    }

    if (tierSelect) {
      var tiers = distinctSorted(usageRows, "event_tier");
      fillSelect(tierSelect, tiers, "Overall");
      tierSelect.addEventListener("change", drawUsage);
    }
    renderTypeFilterChips(typeFilterEl, selectedTypes, drawUsage);
    [roleSelect, shareMin, shareMax, speedMin, speedMax].forEach(function (el) {
      if (!el) return;
      el.addEventListener("input", drawUsage);
      el.addEventListener("change", drawUsage);
    });
    drawUsage();

    var winRows = marts.pokemon_win_rate_summary || [];
    var winGrid = document.getElementById("win-rate-grid");
    var winTable = document.getElementById("win-rate-table");
    var minRecordSelect = document.getElementById("win-rate-min-record-count-filter");
    var winSortable = winTable
      ? makeSortableTable(
          winTable,
          [],
          function (r, i) {
            return (
              '<td><span class="badge badge-rank">#' + (i + 1) + "</span></td>" +
              "<td>" + pokemonCell(r.pokemon_key, r.pokemon_name) + "</td>" +
              "<td>" + formatPercent(r.win_rate) + ' <span class="ranked-value">(n=' + r.record_count + ")</span></td>"
            );
          },
          { defaultKey: "win_rate" }
        )
      : null;
    function updateWinRows() {
      var floor = minRecordSelect ? parseInt(minRecordSelect.value, 10) : 5;
      var filtered = winRows
        .filter(function (r) {
          return r.record_count >= floor;
        })
        .slice()
        .sort(function (a, b) {
          return b.win_rate - a.win_rate;
        });
      renderGrid6xn(winGrid, filtered.slice(0, 18), {
        keyFn: function (r) {
          return r.pokemon_key;
        },
        labelFn: function (r) {
          return r.pokemon_name;
        },
        displayFn: function (r) {
          return formatPercent(r.win_rate);
        },
        subFn: function (r) {
          return "n=" + r.record_count;
        },
      });
      if (winSortable) winSortable.setRows(filtered.slice(0, 30));
    }
    if (minRecordSelect) minRecordSelect.addEventListener("change", updateWinRows);
    updateWinRows();

    setupUsageTrends();

    setupSubTabs(
      document.querySelectorAll('.tab-panel[data-panel="usage"] .subtab-btn'),
      document.querySelectorAll('.tab-panel[data-panel="usage"] .subtab-panel')
    );
  }

  // Usage-by-tournament-date subtab (backlog #6's data half; #29/#30's UI
  // half): a date filter (#30) plus a "vs. the previous tournament date"
  // delta per Pokémon (#29's dependency-free stand-in for a line chart —
  // this dashboard has no charting library, see the module docstring
  // above). event_date is a tournament date, not an extraction
  // snapshot_date, so this trend is real even with only one snapshot's
  // worth of staging history.
  function trendDeltaLabel(row) {
    if (row.is_new) return "NEW";
    if (row.usage_share_delta === null || row.usage_share_delta === undefined) return "";
    var points = row.usage_share_delta * 100;
    var arrow = points > 0 ? "▲" : points < 0 ? "▼" : "";
    var sign = points > 0 ? "+" : "";
    return arrow + " " + sign + points.toFixed(1) + "pp";
  }

  function trendDeltaBadgeHtml(row) {
    if (row.is_new) return '<span class="badge badge-new">NEW</span>';
    if (row.usage_share_delta === null || row.usage_share_delta === undefined) return "—";
    var points = row.usage_share_delta * 100;
    var cls = points > 0 ? "badge-positive" : points < 0 ? "badge-negative" : "badge-rank";
    return '<span class="badge ' + cls + '">' + escapeHtml(trendDeltaLabel(row)) + "</span>";
  }

  function setupUsageTrends() {
    var trendRows = marts.pokemon_usage_by_event_date || [];
    var dateSelect = document.getElementById("usage-trend-date-filter");
    var grid = document.getElementById("usage-trend-grid");
    var table = document.getElementById("usage-trend-table");
    var dates = distinctSorted(trendRows, "event_date").slice().reverse(); // most recent first

    var tableSortable = table
      ? makeSortableTable(
          table,
          [],
          function (r) {
            return (
              '<td><span class="badge badge-rank">#' + r.usage_rank + "</span></td>" +
              "<td>" + pokemonCell(r.pokemon_key, r.pokemon_name) + "</td>" +
              "<td>" + formatPercent(r.usage_share) + "</td>" +
              "<td>" + trendDeltaBadgeHtml(r) + "</td>"
            );
          },
          { defaultKey: "usage_rank", defaultDir: "asc" }
        )
      : null;

    function rowsForDate(date) {
      var dateIndex = dates.indexOf(date);
      var prevDate = dateIndex >= 0 && dateIndex < dates.length - 1 ? dates[dateIndex + 1] : null;
      var prevByKey = {};
      if (prevDate) {
        trendRows.forEach(function (r) {
          if (r.event_date === prevDate) prevByKey[r.pokemon_key] = r;
        });
      }
      // No prevDate at all (the earliest tournament date on record) means
      // there is nothing to compare against, full stop -- distinct from a
      // specific Pokémon genuinely being new as of `date`, which only
      // applies once a prevDate exists to have been absent from.
      return trendRows
        .filter(function (r) {
          return r.event_date === date;
        })
        .map(function (r) {
          var prev = prevByKey[r.pokemon_key];
          return {
            pokemon_key: r.pokemon_key,
            pokemon_name: r.pokemon_name,
            usage_rank: r.usage_rank,
            usage_share: r.usage_share,
            usage_share_delta: prev ? r.usage_share - prev.usage_share : null,
            is_new: !!prevDate && !prev,
          };
        })
        .sort(function (a, b) {
          return a.usage_rank - b.usage_rank;
        });
    }

    function drawTrend() {
      var date = dateSelect ? dateSelect.value : dates[0];
      var rows = rowsForDate(date);
      renderGrid6xn(grid, rows.slice(0, 18), {
        keyFn: function (r) {
          return r.pokemon_key;
        },
        labelFn: function (r) {
          return r.pokemon_name;
        },
        displayFn: function (r) {
          return formatPercent(r.usage_share);
        },
        subFn: trendDeltaLabel,
      });
      if (tableSortable) tableSortable.setRows(rows.slice(0, 30));
    }

    if (dateSelect) {
      dateSelect.innerHTML = "";
      dates.forEach(function (date) {
        var opt = document.createElement("option");
        opt.value = date;
        opt.textContent = date;
        dateSelect.appendChild(opt);
      });
      dateSelect.addEventListener("change", drawTrend);
    }
    drawTrend();
  }

  // Pokémon Profile: one Pokémon-centric view combining base stats + type,
  // then three separated Items/Ability/Moves sections (docs/design-system.md's
  // "Item / Ability / Move separation" — replaces the old single combined
  // build table), each capped and described, plus Team Cores.
  function setupPokemonProfile() {
    var profileRows = marts.pokemon_champions_profile || [];
    var itemRows = marts.pokemon_item_usage || [];
    var abilityRows = marts.pokemon_ability_usage || [];
    var moveRows = marts.pokemon_move_usage || [];
    var coreRows = marts.pokemon_team_core_usage || [];

    var select = document.getElementById("pokemon-profile-filter");
    if (!select) return;

    var sortedProfiles = profileRows.slice().sort(function (a, b) {
      return (b.usage_share || 0) - (a.usage_share || 0);
    });
    fillSelect(
      select,
      sortedProfiles.map(function (r) {
        return r.pokemon_name;
      }),
      "Select a Pokémon…"
    );

    var statsEl = document.getElementById("pokemon-profile-stats");
    var itemGrid = document.getElementById("profile-item-grid");
    var abilityGrid = document.getElementById("profile-ability-grid");
    var moveTable = document.getElementById("profile-move-table");
    var moveTableSortable = moveTable
      ? makeSortableTable(
          moveTable,
          [],
          function (r) {
            return (
              "<td>" + typeIconImg(r.move_type, 18) + " " + escapeHtml(r.move_name) + "</td>" +
              "<td>" + formatPercent(r.move_share) + "</td>" +
              "<td>" + escapeHtml(r.category || "—") + "</td>" +
              "<td>" + (r.power != null ? r.power : "—") + "</td>" +
              "<td>" + (r.accuracy != null ? r.accuracy + "%" : "—") + "</td>" +
              "<td>" + (r.pp != null ? r.pp : "—") + "</td>" +
              "<td>" + (r.priority || 0) + "</td>" +
              "<td>" + escapeHtml(r.short_effect || "") + "</td>"
            );
          },
          { defaultKey: "usage_rank", defaultDir: "asc" }
        )
      : null;
    var coreGrid = document.getElementById("profile-team-core-grid");

    function render(chosenName) {
      var profile = sortedProfiles.filter(function (r) {
        return r.pokemon_name === chosenName;
      })[0];

      if (statsEl) {
        if (!profile) {
          statsEl.className = "empty-state";
          statsEl.textContent = "Select a Pokémon to see its profile.";
        } else {
          statsEl.className = "";
          statsEl.innerHTML =
            '<div class="cell-with-icon">' +
            spriteImg(profile.pokemon_key, ICON_SIZES.lg) +
            "<div><strong>" + escapeHtml(profile.pokemon_name) + "</strong> " +
            speedTierBadge(profile.speed) +
            '<div class="type-badge-row type-badge-lg" id="profile-type-badge"></div>' +
            "HP " + profile.hp + " · Atk " + profile.attack + " · Def " + profile.defense +
            " · SpA " + profile.sp_attack + " · SpD " + profile.sp_defense +
            " · Spe " + profile.speed + "<br>" +
            formatPercent(profile.usage_share) + " usage · " + formatPercent(profile.win_rate) +
            " win rate</div></div>";
          renderTypeBadgeRow(document.getElementById("profile-type-badge"), profile.type_1, profile.type_2, true);
        }
      }

      var items = chosenName
        ? itemRows
            .filter(function (r) {
              return r.pokemon_name === chosenName;
            })
            .sort(function (a, b) {
              return a.usage_rank - b.usage_rank;
            })
            .slice(0, 5)
        : [];
      renderGrid6xn(itemGrid, items, {
        iconFn: function (r) {
          return itemIcons[r.item_name];
        },
        labelFn: function (r) {
          return r.item_name;
        },
        displayFn: function (r) {
          return formatPercent(r.item_share);
        },
        subFn: function (r) {
          return r.short_effect;
        },
      });

      var abilities = chosenName
        ? abilityRows
            .filter(function (r) {
              return r.pokemon_name === chosenName;
            })
            .sort(function (a, b) {
              return a.usage_rank - b.usage_rank;
            })
            .slice(0, 5)
        : [];
      renderGrid6xn(abilityGrid, abilities, {
        labelFn: function (r) {
          return r.ability;
        },
        displayFn: function (r) {
          return formatPercent(r.ability_share);
        },
        subFn: function (r) {
          return r.short_effect;
        },
      });

      var moves = chosenName
        ? moveRows
            .filter(function (r) {
              return r.pokemon_name === chosenName;
            })
            .sort(function (a, b) {
              return a.usage_rank - b.usage_rank;
            })
            .slice(0, 15)
        : [];
      if (moveTableSortable) moveTableSortable.setRows(moves);

      var cores = chosenName
        ? coreRows
            .filter(function (r) {
              return r.pokemon_name === chosenName;
            })
            .sort(function (a, b) {
              return a.usage_rank - b.usage_rank;
            })
            .slice(0, 15)
        : [];
      renderGrid6xn(coreGrid, cores, {
        keyFn: function (r) {
          return r.partner_pokemon_key;
        },
        labelFn: function (r) {
          return r.partner_pokemon_name;
        },
        displayFn: function (r) {
          return formatPercent(r.partner_share);
        },
      });
    }

    select.addEventListener("change", function () {
      render(select.value);
    });
    if (sortedProfiles.length) select.value = sortedProfiles[0].pokemon_name;
    render(select.value);

    setupSubTabs(
      document.querySelectorAll('.tab-panel[data-panel="pokemon-profile"] .subtab-btn'),
      document.querySelectorAll('.tab-panel[data-panel="pokemon-profile"] .subtab-panel')
    );
  }

  function setupSpeedTiers() {
    var rows = (marts.pokemon_champions_profile || []).slice().sort(function (a, b) {
      return b.speed - a.speed;
    });
    var minEl = document.getElementById("speed-tiers-min");
    var maxEl = document.getElementById("speed-tiers-max");
    var typeFilterEl = document.getElementById("speed-tiers-type-filter");
    var selectedTypes = {};
    var grid = document.getElementById("speed-grid");
    var table = document.getElementById("speed-tiers-table");

    var tableSortable = table
      ? makeSortableTable(
          table,
          [],
          function (r, i) {
            return (
              '<td><span class="badge badge-rank">#' + (i + 1) + "</span></td>" +
              "<td>" + pokemonCell(r.pokemon_key, r.pokemon_name) + "</td>" +
              "<td>" + r.speed + "</td>" +
              "<td>" + speedTierBadge(r.speed) + "</td>" +
              "<td>" + formatPercent(r.usage_share) + "</td>" +
              "<td>" + formatPercent(r.win_rate) + "</td>"
            );
          },
          { defaultKey: "speed" }
        )
      : null;

    function filtered() {
      return rows.filter(function (r) {
        if (!passesTypeFilter(selectedTypes, r.type_1, r.type_2)) return false;
        if (!inRange(r.speed, minEl, maxEl)) return false;
        return true;
      });
    }

    function draw() {
      var f = filtered();
      renderGrid6xn(grid, f.slice(0, 18), {
        keyFn: function (r) {
          return r.pokemon_key;
        },
        labelFn: function (r) {
          return r.pokemon_name;
        },
        displayFn: function (r) {
          return String(r.speed);
        },
        subFn: function (r) {
          return speedTier(r.speed).label;
        },
      });
      if (tableSortable) tableSortable.setRows(f);
    }

    renderTypeFilterChips(typeFilterEl, selectedTypes, draw);
    [minEl, maxEl].forEach(function (el) {
      if (!el) return;
      el.addEventListener("input", draw);
    });
    draw();
  }

  registerTab("overview", setupOverview);
  registerTab("usage", setupUsage);
  registerTab("pokemon-profile", setupPokemonProfile);
  registerTab("speed-tiers", setupSpeedTiers);

  setupTabs(function (tabId) {
    if (!initialized[tabId] && tabInitializers[tabId]) {
      initialized[tabId] = true;
      tabInitializers[tabId]();
    }
  });

  // Shared namespace for matchup.js/teams.js (loaded right after this
  // file) — avoids duplicating DATA access or any of the helpers above.
  window.DashboardApp = {
    DATA: DATA,
    marts: marts,
    sprites: sprites,
    typeIcons: typeIcons,
    itemIcons: itemIcons,
    pokemonNames: pokemonNames,
    ICON_SIZES: ICON_SIZES,
    ALL_TYPES: ALL_TYPES,
    escapeHtml: escapeHtml,
    distinctSorted: distinctSorted,
    distinctSortedByMetric: distinctSortedByMetric,
    usageShareByKey: usageShareByKey,
    championsProfileByKey: championsProfileByKey,
    roleByKey: roleByKey,
    fillSelect: fillSelect,
    renderRows: renderRows,
    inRange: inRange,
    renderTypeFilterChips: renderTypeFilterChips,
    hasAnySelectedType: hasAnySelectedType,
    passesTypeFilter: passesTypeFilter,
    setupDrilldown: setupDrilldown,
    spriteImg: spriteImg,
    pokemonCell: pokemonCell,
    itemCell: itemCell,
    typeIconImg: typeIconImg,
    renderTypeBadgeRow: renderTypeBadgeRow,
    formatPercent: formatPercent,
    SPEED_TIERS: SPEED_TIERS,
    speedTier: speedTier,
    speedTierBadge: speedTierBadge,
    renderGrid6xn: renderGrid6xn,
    makeSortableTable: makeSortableTable,
    registerTab: registerTab,
    setupSubTabs: setupSubTabs,
  };
})();
