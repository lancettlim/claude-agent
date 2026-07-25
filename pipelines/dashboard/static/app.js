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
    rows.forEach(function (row) {
      var tr = document.createElement("tr");
      tr.innerHTML = rowHtmlFn(row);
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
    if (!canvas || typeof Chart === "undefined") return null;
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

    var winRows = marts.pokemon_win_rate_summary || [];
    var tbody = document.querySelector("#win-rate-table tbody");
    if (tbody) {
      var top = winRows
        .slice()
        .sort(function (a, b) {
          return b.win_rate - a.win_rate;
        })
        .slice(0, 20);
      renderRows(tbody, top, function (r) {
        return (
          "<td>" + pokemonCell(r.pokemon_key, r.pokemon_name) + "</td>" +
          "<td>" + r.total_wins + "</td>" +
          "<td>" + r.total_losses + "</td>" +
          "<td>" + (r.win_rate * 100).toFixed(1) + "%</td>" +
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

  var tabInitializers = {
    usage: setupUsage,
    builds: setupBuild,
    moves: setupMoves,
    "team-cores": setupTeamCores,
  };
  var initialized = {};
  setupTabs(function (tabId) {
    if (!initialized[tabId] && tabInitializers[tabId]) {
      initialized[tabId] = true;
      tabInitializers[tabId]();
    }
  });
})();
