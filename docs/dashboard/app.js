/* Plain vanilla JS — no bundler, no framework. Reads window.DASHBOARD_DATA
 * (baked into index.html by pipelines/dashboard/build.py) and wires up the
 * tabs/filters/charts/tables declared in index.html.jinja.
 *
 * Chart.js canvases inside a hidden (display:none) tab panel initialize at
 * zero size, so each tab's chart-drawing setup is deferred until that tab
 * is first activated (see tabInitializers/setupTabs below) rather than run
 * eagerly on page load. */
(function () {
  "use strict";

  var DATA = window.DASHBOARD_DATA || {
    marts: {},
    kpis: {},
    sprites: {},
    type_icons: {},
    move_types: {},
    item_icons: {},
  };
  var marts = DATA.marts || {};
  var sprites = DATA.sprites || {};
  var typeIcons = DATA.type_icons || {};
  var moveTypes = DATA.move_types || {};
  var itemIcons = DATA.item_icons || {};

  // ---------- generic helpers ----------

  function escapeHtml(value) {
    var map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
    return String(value).replace(/[&<>"']/g, function (c) {
      return map[c];
    });
  }

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

  // A single select-driven drill-down: fills the select from the distinct
  // values of distinctField across rows, defaults to the first option, and
  // calls render(selectedValue) on load and on every change.
  function setupDrilldown(opts) {
    var select = document.getElementById(opts.selectId);
    if (!select) return;
    var options = distinctSorted(opts.rows, opts.distinctField);
    fillSelect(select, options, opts.allLabel || "Select a Pokémon…");
    select.addEventListener("change", function () {
      opts.render(select.value);
    });
    if (options.length) {
      select.value = options[0];
    }
    opts.render(select.value);
  }

  // ---------- sprite/icon cell + chart-axis rendering ----------

  function spriteImg(pokemonKey, sizePx) {
    var src = sprites[pokemonKey];
    if (!src) return "";
    var size = sizePx || 24;
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

  // Image preload cache shared by the sprite-axis chart plugin and the
  // external tooltip helper, so the same source is only fetched once and a
  // chart redraws itself (without animation) the moment an image loads.
  var imageCache = {};
  function getImage(src, chart) {
    if (!src) return null;
    var cached = imageCache[src];
    if (cached) return cached.img;
    var img = new Image();
    var entry = { img: img, notified: false };
    imageCache[src] = entry;
    img.onload = function () {
      if (chart && !entry.notified) {
        entry.notified = true;
        chart.update("none");
      }
    };
    img.src = src;
    return img;
  }

  // Chart.js plugin (native plugin API): draws a small sprite below each
  // x-axis tick, for bar charts whose axis is a list of Pokémon. Reserves
  // extra bottom space via the chart's own layout.padding so the plot area
  // doesn't overlap the sprites.
  var spriteAxisPlugin = {
    id: "spriteAxis",
    afterDraw: function (chart) {
      var opts = chart.config.options.plugins && chart.config.options.plugins.spriteAxis;
      var scale = chart.scales.x;
      if (!opts || !opts.sources || !scale) return;
      var ctx = chart.ctx;
      var size = 22;
      opts.sources.forEach(function (src, i) {
        var img = getImage(src, chart);
        if (!img || !img.complete || !img.naturalWidth) return;
        var x = scale.getPixelForTick(i);
        var y = scale.bottom + 6;
        ctx.drawImage(img, Math.round(x - size / 2), y, size, size);
      });
    },
  };

  // Chart.js's documented "external tooltip" recipe: canvas-drawn tooltips
  // can't embed an <img>, so we disable the built-in tooltip and position
  // an absolutely-placed DOM element (see .chart-tooltip in the template's
  // <style>) inside the chart's .chart-wrap container instead.
  function externalTooltipHandler(getInfo) {
    return function (context) {
      var chart = context.chart;
      var tooltipModel = context.tooltip;
      var wrap = chart.canvas.parentNode;
      var el = wrap.querySelector(".chart-tooltip");
      if (!el) {
        el = document.createElement("div");
        el.className = "chart-tooltip";
        wrap.appendChild(el);
      }
      if (tooltipModel.opacity === 0) {
        el.style.opacity = 0;
        return;
      }
      var dataIndex =
        tooltipModel.dataPoints && tooltipModel.dataPoints.length
          ? tooltipModel.dataPoints[0].dataIndex
          : null;
      var info = dataIndex != null ? getInfo(dataIndex) : null;
      el.innerHTML = "";
      if (info) {
        if (info.iconSrc) {
          var img = document.createElement("img");
          img.src = info.iconSrc;
          el.appendChild(img);
        }
        var span = document.createElement("span");
        span.textContent = info.text;
        el.appendChild(span);
      }
      el.style.opacity = 1;
      el.style.left = tooltipModel.caretX + "px";
      el.style.top = tooltipModel.caretY + "px";
    };
  }

  // Single shared bar-chart helper (folds in what used to be the
  // now-removed duplicate inline Chart.js blocks in the tier/moves setup
  // functions). spriteSources/tooltipInfoFn are both optional.
  function drawBarChart(canvasId, config) {
    var canvas = document.getElementById(canvasId);
    if (!canvas) return null;
    var wrap = canvas.parentNode;
    if (typeof Chart === "undefined") {
      // Chart.js didn't load (e.g. the CDN is unreachable). Collapse the
      // reserved chart area instead of leaving a blank box the height of a
      // chart — the table below still has the full data.
      if (wrap) wrap.style.display = "none";
      return null;
    }
    if (wrap) wrap.style.display = "";
    var options = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true } },
    };
    var chartPlugins = [];
    if (config.spriteSources) {
      options.layout = { padding: { bottom: 28 } };
      options.plugins.spriteAxis = { sources: config.spriteSources };
      chartPlugins.push(spriteAxisPlugin);
    }
    if (config.tooltipInfoFn) {
      options.plugins.tooltip = { enabled: false, external: externalTooltipHandler(config.tooltipInfoFn) };
    }
    return new Chart(canvas, {
      type: "bar",
      data: {
        labels: config.labels,
        datasets: [{ label: config.label, data: config.values, backgroundColor: "#2b5cad" }],
      },
      options: options,
      plugins: chartPlugins,
    });
  }

  // ---------- tab switching ----------

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

  // ---------- per-tab setup (each called once, on first activation) ----------

  function setupUsage() {
    var usageRows = marts.pokemon_usage_summary || [];
    var tierSelect = document.getElementById("usage-tier-filter");
    if (tierSelect) {
      var tiers = distinctSorted(usageRows, "event_tier");
      fillSelect(tierSelect, tiers, "Overall");
      var chart = null;
      var drawUsageChart = function () {
        var tier = tierSelect.value;
        var rows = usageRows
          .filter(function (r) {
            return (r.event_tier || "") === tier;
          })
          .sort(function (a, b) {
            return a.usage_rank - b.usage_rank;
          })
          .slice(0, 15);
        if (chart) chart.destroy();
        chart = drawBarChart("usage-chart", {
          labels: rows.map(function (r) {
            return r.pokemon_name;
          }),
          values: rows.map(function (r) {
            return r.usage_count;
          }),
          label: "Roster appearances",
          spriteSources: rows.map(function (r) {
            return sprites[r.pokemon_key];
          }),
          tooltipInfoFn: function (i) {
            var r = rows[i];
            return { iconSrc: sprites[r.pokemon_key], text: r.pokemon_name + ": " + r.usage_count };
          },
        });
      };
      tierSelect.addEventListener("change", drawUsageChart);
      drawUsageChart();
    }

    var usageLeadersBody = document.querySelector("#usage-leaders-table tbody");
    if (usageLeadersBody) {
      var leaders = usageRows
        .filter(function (r) {
          return !r.event_tier;
        })
        .slice()
        .sort(function (a, b) {
          return a.usage_rank - b.usage_rank;
        })
        .slice(0, 20);
      renderRows(usageLeadersBody, leaders, function (r) {
        return (
          '<td><span class="badge badge-rank">#' + r.usage_rank + "</span></td>" +
          "<td>" + pokemonCell(r.pokemon_key, r.pokemon_name) + "</td>" +
          "<td>" + r.usage_count + "</td>" +
          "<td>" + formatPercent(r.usage_share) + "</td>"
        );
      });
    }

    var winRows = marts.pokemon_win_rate_summary || [];
    var tbody = document.querySelector("#win-rate-table tbody");
    if (tbody) {
      var top = winRows
        .slice()
        .sort(function (a, b) {
          return b.win_rate - a.win_rate;
        })
        .slice(0, 20);
      renderRows(tbody, top, function (r, i) {
        return (
          '<td><span class="badge badge-rank">#' + (i + 1) + "</span></td>" +
          "<td>" + pokemonCell(r.pokemon_key, r.pokemon_name) + "</td>" +
          "<td>" + r.total_wins + "</td>" +
          "<td>" + r.total_losses + "</td>" +
          "<td>" + formatPercent(r.win_rate) + "</td>" +
          "<td>" + r.record_count + "</td>"
        );
      });
    }
  }

  function setupBuild() {
    var rows = marts.pokemon_build_usage || [];
    setupDrilldown({
      rows: rows,
      selectId: "build-pokemon-filter",
      distinctField: "pokemon_name",
      render: function (chosen) {
        var tbody = document.querySelector("#build-table tbody");
        if (!tbody) return;
        var filtered = chosen
          ? rows
              .filter(function (r) {
                return r.pokemon_name === chosen;
              })
              .sort(function (a, b) {
                return a.usage_rank - b.usage_rank;
              })
          : [];
        renderRows(tbody, filtered, function (r) {
          return (
            "<td>" + itemCell(r.item_name) + "</td>" +
            "<td>" + (r.ability ? escapeHtml(r.ability) : "—") + "</td>" +
            "<td>" + r.usage_count + "</td>"
          );
        });
      },
    });
  }

  function setupMoves() {
    var rows = marts.pokemon_move_usage || [];
    var chart = null;
    setupDrilldown({
      rows: rows,
      selectId: "move-pokemon-filter",
      distinctField: "pokemon_name",
      render: function (chosen) {
        var filtered = chosen
          ? rows
              .filter(function (r) {
                return r.pokemon_name === chosen;
              })
              .sort(function (a, b) {
                return a.usage_rank - b.usage_rank;
              })
          : [];
        if (chart) chart.destroy();
        chart = drawBarChart("move-chart", {
          labels: filtered.map(function (r) {
            return r.move_name;
          }),
          values: filtered.map(function (r) {
            return r.usage_count;
          }),
          label: "Usage count",
          tooltipInfoFn: function (i) {
            var r = filtered[i];
            return {
              iconSrc: typeIcons[moveTypes[r.move_name]],
              text: r.move_name + ": " + r.usage_count,
            };
          },
        });

        var tbody = document.querySelector("#move-table tbody");
        if (tbody) {
          renderRows(tbody, filtered, function (r) {
            var typeSrc = typeIcons[moveTypes[r.move_name]];
            var icon = typeSrc ? '<img class="cell-icon" src="' + typeSrc + '" alt="">' : "";
            return (
              '<td><div class="cell-with-icon">' + icon + "<span>" + escapeHtml(r.move_name) + "</span></div></td>" +
              "<td>" + r.usage_count + "</td>"
            );
          });
        }
      },
    });
  }

  function setupTeamCores() {
    var rows = marts.pokemon_team_core_usage || [];
    var chart = null;
    setupDrilldown({
      rows: rows,
      selectId: "team-core-pokemon-filter",
      distinctField: "pokemon_name",
      render: function (chosen) {
        var filtered = chosen
          ? rows
              .filter(function (r) {
                return r.pokemon_name === chosen;
              })
              .sort(function (a, b) {
                return a.usage_rank - b.usage_rank;
              })
          : [];
        var top = filtered.slice(0, 15);

        if (chart) chart.destroy();
        chart = drawBarChart("team-core-chart", {
          labels: top.map(function (r) {
            return r.partner_pokemon_name;
          }),
          values: top.map(function (r) {
            return r.co_occurrence_count;
          }),
          label: "Co-occurrence count",
          spriteSources: top.map(function (r) {
            return sprites[r.partner_pokemon_key];
          }),
          tooltipInfoFn: function (i) {
            var r = top[i];
            return {
              iconSrc: sprites[r.partner_pokemon_key],
              text: r.partner_pokemon_name + ": " + r.co_occurrence_count,
            };
          },
        });

        var tbody = document.querySelector("#team-core-table tbody");
        if (tbody) {
          renderRows(tbody, filtered, function (r) {
            return (
              "<td>" + pokemonCell(r.partner_pokemon_key, r.partner_pokemon_name) + "</td>" +
              "<td>" + r.co_occurrence_count + "</td>"
            );
          });
        }
      },
    });
  }

  function setupSpeedTiers() {
    var rows = (marts.pokemon_champions_profile || [])
      .slice()
      .sort(function (a, b) {
        return b.speed - a.speed;
      });

    var top = rows.slice(0, 20);
    drawBarChart("speed-chart", {
      labels: top.map(function (r) {
        return r.pokemon_name;
      }),
      values: top.map(function (r) {
        return r.speed;
      }),
      label: "Speed",
      spriteSources: top.map(function (r) {
        return sprites[r.pokemon_key];
      }),
      tooltipInfoFn: function (i) {
        var r = top[i];
        return { iconSrc: sprites[r.pokemon_key], text: r.pokemon_name + ": " + r.speed + " speed" };
      },
    });

    var tbody = document.querySelector("#speed-tiers-table tbody");
    if (tbody) {
      renderRows(tbody, rows, function (r, i) {
        return (
          '<td><span class="badge badge-rank">#' + (i + 1) + "</span></td>" +
          "<td>" + pokemonCell(r.pokemon_key, r.pokemon_name) + "</td>" +
          "<td>" + r.speed + "</td>" +
          "<td>" + speedTierBadge(r.speed) + "</td>" +
          "<td>" + formatPercent(r.usage_share) + "</td>" +
          "<td>" + formatPercent(r.win_rate) + "</td>"
        );
      });
    }
  }

  // Fully client-side (no backend): lets a visitor assemble a roster of up
  // to 6 from the current legal pool (pokemon_champions_profile), ordered
  // by usage/win-rate/speed per docs/design-system.md's ordering
  // convention, and see their picks' speed order — reusing the same
  // speed-tier bucketing as the Speed Tiers tab. Persisted to
  // localStorage only; never sent anywhere.
  function setupTeamBuilder() {
    var rows = marts.pokemon_champions_profile || [];
    var byKey = {};
    rows.forEach(function (r) {
      byKey[r.pokemon_key] = r;
    });

    var STORAGE_KEY = "pokemonChampionsTeamBuilder";
    var MAX_TEAM_SIZE = 6;
    var team = [];
    try {
      var saved = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "[]");
      team = saved.filter(function (key) {
        return byKey[key];
      }).slice(0, MAX_TEAM_SIZE);
    } catch (e) {
      team = [];
    }

    var searchInput = document.getElementById("team-builder-search");
    var sortSelect = document.getElementById("team-builder-sort");
    var availableList = document.getElementById("team-builder-available");
    var slotsEl = document.getElementById("team-builder-slots");
    var countEl = document.getElementById("team-builder-count");
    var speedOrderEl = document.getElementById("team-builder-speed-order");
    var summaryEl = document.getElementById("team-builder-summary");
    var clearBtn = document.getElementById("team-builder-clear");

    function persist() {
      try {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(team));
      } catch (e) {
        // localStorage unavailable (private browsing, etc.) — the team
        // just won't survive a reload; not fatal.
      }
    }

    function addToTeam(key) {
      if (team.length >= MAX_TEAM_SIZE || team.indexOf(key) !== -1) return;
      team.push(key);
      persist();
      renderAll();
    }

    function removeFromTeam(key) {
      team = team.filter(function (k) {
        return k !== key;
      });
      persist();
      renderAll();
    }

    function renderAvailable() {
      if (!availableList) return;
      var query = ((searchInput && searchInput.value) || "").trim().toLowerCase();
      var sortBy = sortSelect ? sortSelect.value : "usage";
      var candidates = rows.filter(function (r) {
        return team.indexOf(r.pokemon_key) === -1 && r.pokemon_name.toLowerCase().indexOf(query) !== -1;
      });
      candidates.sort(function (a, b) {
        if (sortBy === "win_rate") return (b.win_rate || 0) - (a.win_rate || 0);
        if (sortBy === "speed") return (b.speed || 0) - (a.speed || 0);
        return (b.usage_count || 0) - (a.usage_count || 0);
      });
      var full = team.length >= MAX_TEAM_SIZE;
      availableList.innerHTML = "";
      candidates.slice(0, 50).forEach(function (r) {
        var li = document.createElement("li");
        li.className = "roster-item";
        li.innerHTML =
          spriteImg(r.pokemon_key, 32) +
          '<div class="roster-info"><div class="roster-name">' + escapeHtml(r.pokemon_name) + "</div>" +
          '<div class="roster-sub">' + formatPercent(r.usage_share) + " usage · " +
          formatPercent(r.win_rate) + " win rate · " + (r.speed != null ? r.speed : "—") + " speed</div></div>" +
          '<button class="btn btn-sm" type="button"' + (full ? " disabled" : "") + ">Add</button>";
        li.querySelector("button").addEventListener("click", function () {
          addToTeam(r.pokemon_key);
        });
        availableList.appendChild(li);
      });
      if (!candidates.length) {
        var empty = document.createElement("li");
        empty.className = "roster-item";
        empty.textContent = "No Pokémon match your search.";
        availableList.appendChild(empty);
      }
    }

    // A named helper (rather than inline logic in renderSlots' for loop)
    // so each slot's remove handler closes over its own `key` — a `var`
    // declared inside a for-loop body is function-scoped, not
    // block-scoped, so handlers built directly in the loop would all end
    // up capturing the loop's final value instead of their own slot's.
    function buildSlotElement(key) {
      var slot = document.createElement("div");
      if (key && byKey[key]) {
        var r = byKey[key];
        slot.className = "team-slot";
        slot.innerHTML =
          (sprites[key] ? '<img src="' + sprites[key] + '" alt="">' : "") +
          '<div class="slot-name">' + escapeHtml(r.pokemon_name) + "</div>" +
          '<button class="btn-remove" type="button" aria-label="Remove ' + escapeHtml(r.pokemon_name) + '">Remove</button>';
        slot.querySelector("button").addEventListener("click", function () {
          removeFromTeam(key);
        });
      } else {
        slot.className = "team-slot empty";
        slot.textContent = "Empty slot";
      }
      return slot;
    }

    function renderSlots() {
      if (!slotsEl) return;
      slotsEl.innerHTML = "";
      for (var i = 0; i < MAX_TEAM_SIZE; i++) {
        slotsEl.appendChild(buildSlotElement(team[i]));
      }
      if (countEl) countEl.textContent = String(team.length);
      if (clearBtn) clearBtn.disabled = team.length === 0;
    }

    function renderSpeedOrder() {
      if (!speedOrderEl) return;
      var members = team
        .map(function (key) {
          return byKey[key];
        })
        .filter(Boolean)
        .sort(function (a, b) {
          return (b.speed || 0) - (a.speed || 0);
        });
      speedOrderEl.innerHTML = "";
      if (!members.length) {
        var li = document.createElement("li");
        li.textContent = "Add Pokémon to your team to see their speed order.";
        speedOrderEl.appendChild(li);
        return;
      }
      members.forEach(function (r) {
        var row = document.createElement("li");
        row.innerHTML =
          spriteImg(r.pokemon_key, 24) +
          "<span>" + escapeHtml(r.pokemon_name) + "</span>" +
          speedTierBadge(r.speed) +
          '<span class="speed-value">' + r.speed + "</span>";
        speedOrderEl.appendChild(row);
      });
    }

    function renderSummary() {
      if (!summaryEl) return;
      var members = team
        .map(function (key) {
          return byKey[key];
        })
        .filter(Boolean);
      function avg(field) {
        var values = members
          .map(function (r) {
            return r[field];
          })
          .filter(function (v) {
            return v !== null && v !== undefined;
          });
        if (!values.length) return null;
        return (
          values.reduce(function (sum, v) {
            return sum + v;
          }, 0) / values.length
        );
      }
      var avgSpeed = avg("speed");
      summaryEl.innerHTML =
        '<div class="stat"><strong>' + (avgSpeed !== null ? Math.round(avgSpeed) : "—") + "</strong>Avg. speed</div>" +
        '<div class="stat"><strong>' + formatPercent(avg("usage_share")) + "</strong>Avg. usage share</div>" +
        '<div class="stat"><strong>' + formatPercent(avg("win_rate")) + "</strong>Avg. win rate</div>";
    }

    function renderAll() {
      renderAvailable();
      renderSlots();
      renderSpeedOrder();
      renderSummary();
    }

    if (searchInput) searchInput.addEventListener("input", renderAvailable);
    if (sortSelect) sortSelect.addEventListener("change", renderAvailable);
    if (clearBtn) {
      clearBtn.addEventListener("click", function () {
        team = [];
        persist();
        renderAll();
      });
    }

    renderAll();
  }

  var tabInitializers = {
    usage: setupUsage,
    builds: setupBuild,
    moves: setupMoves,
    "team-cores": setupTeamCores,
    "speed-tiers": setupSpeedTiers,
    "team-builder": setupTeamBuilder,
  };
  var initialized = {};
  setupTabs(function (tabId) {
    if (!initialized[tabId] && tabInitializers[tabId]) {
      initialized[tabId] = true;
      tabInitializers[tabId]();
    }
  });
})();
