/* Plain vanilla JS — no bundler, no framework. Reads window.DASHBOARD_DATA
 * (baked into index.html by pipelines/dashboard/build.py) and wires up the
 * filters/charts/tables declared in index.html.jinja. */
(function () {
  "use strict";

  var DATA = window.DASHBOARD_DATA || { marts: {}, kpis: {}, flags: {} };
  var marts = DATA.marts || {};

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

  function renderBarChart(canvasId, labels, values, label) {
    var canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === "undefined") return;
    new Chart(canvas, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [{ label: label, data: values, backgroundColor: "#2b5cad" }],
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true } },
      },
    });
  }

  // --- Usage by tournament tier ---
  (function setupUsage() {
    var usageRows = marts.pokemon_usage_summary || [];
    var tierSelect = document.getElementById("usage-tier-filter");
    if (!tierSelect) return;
    var tiers = distinctSorted(usageRows, "event_tier");
    fillSelect(tierSelect, tiers, "Overall");

    var chart = null;
    function draw() {
      var tier = tierSelect.value;
      var rows = usageRows
        .filter(function (r) {
          return (r.event_tier || "") === tier;
        })
        .sort(function (a, b) {
          return a.usage_rank - b.usage_rank;
        })
        .slice(0, 15);
      var labels = rows.map(function (r) {
        return r.pokemon_name;
      });
      var values = rows.map(function (r) {
        return r.usage_count;
      });
      if (chart) chart.destroy();
      var canvas = document.getElementById("usage-chart");
      if (canvas && typeof Chart !== "undefined") {
        chart = new Chart(canvas, {
          type: "bar",
          data: {
            labels: labels,
            datasets: [{ label: "Roster appearances", data: values, backgroundColor: "#2b5cad" }],
          },
          options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true } },
          },
        });
      }
    }
    tierSelect.addEventListener("change", draw);
    draw();
  })();

  // --- Win rate leaders ---
  (function setupWinRate() {
    var rows = marts.pokemon_win_rate_summary || [];
    var tbody = document.querySelector("#win-rate-table tbody");
    if (!tbody) return;
    rows
      .slice()
      .sort(function (a, b) {
        return b.win_rate - a.win_rate;
      })
      .slice(0, 20)
      .forEach(function (r) {
        var tr = document.createElement("tr");
        tr.innerHTML =
          "<td>" + r.pokemon_name + "</td>" +
          "<td>" + r.total_wins + "</td>" +
          "<td>" + r.total_losses + "</td>" +
          "<td>" + (r.win_rate * 100).toFixed(1) + "%</td>" +
          "<td>" + r.record_count + "</td>";
        tbody.appendChild(tr);
      });
  })();

  // --- Build drill-down ---
  (function setupBuild() {
    var rows = marts.pokemon_build_usage || [];
    var select = document.getElementById("build-pokemon-filter");
    var tbody = document.querySelector("#build-table tbody");
    if (!select || !tbody) return;
    var pokemonNames = distinctSorted(rows, "pokemon_name");
    fillSelect(select, pokemonNames, "Select a Pokémon…");

    function draw() {
      tbody.innerHTML = "";
      var chosen = select.value;
      if (!chosen) return;
      rows
        .filter(function (r) {
          return r.pokemon_name === chosen;
        })
        .sort(function (a, b) {
          return a.usage_rank - b.usage_rank;
        })
        .forEach(function (r) {
          var tr = document.createElement("tr");
          tr.innerHTML =
            "<td>" + (r.item_name || "—") + "</td>" +
            "<td>" + (r.ability || "—") + "</td>" +
            "<td>" + r.usage_count + "</td>";
          tbody.appendChild(tr);
        });
    }
    select.addEventListener("change", draw);
    if (pokemonNames.length) {
      select.value = pokemonNames[0];
      draw();
    }
  })();

  // --- Move drill-down ---
  (function setupMoves() {
    var rows = marts.pokemon_move_usage || [];
    var select = document.getElementById("move-pokemon-filter");
    if (!select) return;
    var pokemonNames = distinctSorted(rows, "pokemon_name");
    fillSelect(select, pokemonNames, "Select a Pokémon…");

    var chart = null;
    function draw() {
      var chosen = select.value;
      var filtered = chosen
        ? rows
            .filter(function (r) {
              return r.pokemon_name === chosen;
            })
            .sort(function (a, b) {
              return a.usage_rank - b.usage_rank;
            })
        : [];
      var labels = filtered.map(function (r) {
        return r.move_name;
      });
      var values = filtered.map(function (r) {
        return r.usage_count;
      });
      if (chart) chart.destroy();
      var canvas = document.getElementById("move-chart");
      if (canvas && typeof Chart !== "undefined") {
        chart = new Chart(canvas, {
          type: "bar",
          data: {
            labels: labels,
            datasets: [{ label: "Usage count", data: values, backgroundColor: "#2b5cad" }],
          },
          options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true } },
          },
        });
      }
    }
    select.addEventListener("change", draw);
    if (pokemonNames.length) {
      select.value = pokemonNames[0];
      draw();
    }
  })();

  // --- Stat change leaderboard (only present when not degenerate) ---
  (function setupStatChanges() {
    var tbody = document.querySelector("#stat-change-table tbody");
    if (!tbody) return;
    var rows = marts.stat_change_leaderboard || [];
    rows
      .filter(function (r) {
        return r.stat_total_delta !== 0;
      })
      .sort(function (a, b) {
        return Math.abs(b.stat_total_delta) - Math.abs(a.stat_total_delta);
      })
      .forEach(function (r) {
        var tr = document.createElement("tr");
        tr.innerHTML =
          "<td>" + r.pokemon_name + "</td>" +
          "<td>" + r.direction + "</td>" +
          "<td>" + r.stat_total_delta + "</td>";
        tbody.appendChild(tr);
      });
  })();

  // --- Legal pool trend by regulation (only present when not degenerate) ---
  (function setupLegalityTrend() {
    var canvas = document.getElementById("legality-chart");
    if (!canvas || typeof Chart === "undefined") return;
    var rows = marts.legality_summary_by_regulation || [];
    var dates = distinctSorted(rows, "snapshot_date");
    var regulations = distinctSorted(rows, "regulation_code");
    var byRegulation = {};
    rows.forEach(function (r) {
      byRegulation[r.regulation_code] = byRegulation[r.regulation_code] || {};
      byRegulation[r.regulation_code][r.snapshot_date] = r.legal_pokemon_count;
    });
    var palette = ["#2b5cad", "#c0392b", "#4c9a4c", "#9b59b6", "#d9b92c"];
    var datasets = regulations.map(function (reg, i) {
      return {
        label: reg,
        data: dates.map(function (d) {
          return (byRegulation[reg] || {})[d] || null;
        }),
        borderColor: palette[i % palette.length],
        fill: false,
      };
    });
    new Chart(canvas, {
      type: "line",
      data: { labels: dates, datasets: datasets },
      options: { responsive: true, scales: { y: { beginAtZero: true } } },
    });
  })();
})();
