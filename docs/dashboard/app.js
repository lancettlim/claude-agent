/* Plain vanilla JS — no bundler, no framework, no charting library. Reads
 * window.DASHBOARD_DATA (baked into index.html by pipelines/dashboard/
 * build.py) and wires up the tabs/filters/tables/ranked-lists declared in
 * index.html.jinja.
 *
 * Ranked visuals (see renderRankedList) are plain DOM/CSS bar rows, not
 * canvas charts — this dashboard has no Chart.js/CDN dependency. */
(function () {
  "use strict";

  var DATA = window.DASHBOARD_DATA || {
    marts: {},
    kpis: {},
    sprites: {},
    type_icons: {},
    move_types: {},
    item_icons: {},
    reference_teams: [],
  };
  var marts = DATA.marts || {};
  var sprites = DATA.sprites || {};
  var typeIcons = DATA.type_icons || {};
  var moveTypes = DATA.move_types || {};
  var itemIcons = DATA.item_icons || {};

  // Icon-size tokens (docs/design-system.md's "Icon size scale") — mirrors
  // the --icon-sm/md/lg CSS custom properties in index.html.jinja.
  var ICON_SIZES = { sm: 32, md: 48, lg: 72 };

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

  // ---------- ranked list (replaces Chart.js bar charts) ----------

  // Renders a dependency-free "ranked percentage/value row" list into
  // container (a <ol>/<ul>/<div>). opts:
  //   keyFn(row)      -> pokemon_key to look up a sprite icon (optional)
  //   iconFn(row)     -> an icon src directly, overrides keyFn (optional)
  //   labelFn(row)    -> row label text
  //   valueFn(row)    -> number driving the bar's relative width
  //   displayFn(row)  -> text shown at the row's right edge
  //   maxValue        -> optional override; defaults to the max valueFn
  //                      among the given rows (bars are relative to each
  //                      other within the list, not to a fixed 100%)
  function renderRankedList(container, rows, opts) {
    if (!container) return;
    container.innerHTML = "";
    if (!rows.length) {
      var empty = document.createElement("li");
      empty.className = "empty-state";
      empty.textContent = "No data yet.";
      container.appendChild(empty);
      return;
    }
    var maxValue = opts.maxValue;
    if (maxValue === undefined) {
      maxValue = rows.reduce(function (max, row) {
        return Math.max(max, opts.valueFn(row) || 0);
      }, 0);
    }
    rows.forEach(function (row, i) {
      var value = opts.valueFn(row) || 0;
      var pct = maxValue > 0 ? Math.min(100, (value / maxValue) * 100) : 0;
      var iconSrc = opts.iconFn ? opts.iconFn(row) : opts.keyFn ? sprites[opts.keyFn(row)] : null;
      var li = document.createElement("li");
      li.className = "ranked-row" + (i === 0 ? " is-leader" : "");
      li.innerHTML =
        '<span class="ranked-rank">#' + (i + 1) + "</span>" +
        (iconSrc ? '<img class="ranked-icon" src="' + iconSrc + '" alt="">' : "") +
        '<div class="ranked-body">' +
        '<div class="ranked-label"><span>' + escapeHtml(opts.labelFn(row)) + '</span><span class="ranked-value">' +
        escapeHtml(opts.displayFn(row)) + "</span></div>" +
        '<div class="ranked-bar-track"><div class="ranked-bar-fill" style="width:' + pct + '%"></div></div>' +
        "</div>";
      container.appendChild(li);
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

  function setupOverview() {
    var top12 = (DATA.kpis && DATA.kpis.top_12_pokemon) || [];
    var top30 = (DATA.kpis && DATA.kpis.top_30_pokemon) || [];

    var grid = document.getElementById("overview-top-12");
    if (grid) {
      grid.innerHTML = "";
      if (!top12.length) {
        grid.innerHTML = '<p class="empty-state">No usage data yet.</p>';
      }
      top12.forEach(function (r, i) {
        var card = document.createElement("div");
        card.className = "spotlight-card";
        card.innerHTML =
          '<span class="badge badge-rank">#' + (i + 1) + "</span>" +
          (sprites[r.pokemon_key]
            ? '<img src="' + sprites[r.pokemon_key] + '" alt="">'
            : "") +
          '<div class="spotlight-name">' + escapeHtml(r.pokemon_name) + "</div>" +
          '<div class="spotlight-stats">' + formatPercent(r.usage_share) + " usage · " +
          formatPercent(r.win_rate) + " win rate</div>";
        grid.appendChild(card);
      });
    }

    var list = document.getElementById("overview-top-30");
    var toggleBtn = document.getElementById("overview-top-30-toggle");
    var expanded = false;
    var maxShare = top30.length ? (top30[0].usage_share || 0) * 100 : 0;
    function renderTop30() {
      var rows = expanded ? top30 : top30.slice(0, 10);
      renderRankedList(list, rows, {
        keyFn: function (r) {
          return r.pokemon_key;
        },
        labelFn: function (r) {
          return r.pokemon_name;
        },
        valueFn: function (r) {
          return (r.usage_share || 0) * 100;
        },
        displayFn: function (r) {
          return formatPercent(r.usage_share);
        },
        maxValue: maxShare,
      });
    }
    if (toggleBtn) {
      toggleBtn.addEventListener("click", function () {
        expanded = !expanded;
        toggleBtn.textContent = expanded ? "Show top 10" : "Show all 30";
        renderTop30();
      });
    }
    renderTop30();
  }

  function setupUsage() {
    var usageRows = marts.pokemon_usage_summary || [];
    var tierSelect = document.getElementById("usage-tier-filter");
    var rankedList = document.getElementById("usage-ranked-list");

    function drawUsageRanked() {
      var tier = tierSelect ? tierSelect.value : "";
      var rows = usageRows
        .filter(function (r) {
          return (r.event_tier || "") === tier;
        })
        .slice()
        .sort(function (a, b) {
          return a.usage_rank - b.usage_rank;
        })
        .slice(0, 15);
      renderRankedList(rankedList, rows, {
        keyFn: function (r) {
          return r.pokemon_key;
        },
        labelFn: function (r) {
          return r.pokemon_name;
        },
        valueFn: function (r) {
          return (r.usage_share || 0) * 100;
        },
        displayFn: function (r) {
          return formatPercent(r.usage_share);
        },
      });
    }
    if (tierSelect) {
      var tiers = distinctSorted(usageRows, "event_tier");
      fillSelect(tierSelect, tiers, "Overall");
      tierSelect.addEventListener("change", drawUsageRanked);
    }
    drawUsageRanked();

    var usageTable = document.getElementById("usage-leaders-table");
    if (usageTable) {
      var leaders = usageRows
        .filter(function (r) {
          return !r.event_tier;
        })
        .slice()
        .sort(function (a, b) {
          return a.usage_rank - b.usage_rank;
        })
        .slice(0, 30);
      makeSortableTable(
        usageTable,
        leaders,
        function (r) {
          return (
            '<td><span class="badge badge-rank">#' + r.usage_rank + "</span></td>" +
            "<td>" + pokemonCell(r.pokemon_key, r.pokemon_name) + "</td>" +
            "<td>" + formatPercent(r.usage_share) + "</td>"
          );
        },
        {}
      );
    }

    var winRows = marts.pokemon_win_rate_summary || [];
    var winTable = document.getElementById("win-rate-table");
    var minRecordSelect = document.getElementById("win-rate-min-record-count-filter");
    if (winTable) {
      var winSortable = makeSortableTable(
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
      );
      function updateWinRows() {
        var floor = minRecordSelect ? parseInt(minRecordSelect.value, 10) : 5;
        var filtered = winRows
          .filter(function (r) {
            return r.record_count >= floor;
          })
          .slice()
          .sort(function (a, b) {
            return b.win_rate - a.win_rate;
          })
          .slice(0, 30);
        winSortable.setRows(filtered);
      }
      if (minRecordSelect) minRecordSelect.addEventListener("change", updateWinRows);
      updateWinRows();
    }
  }

  // Merges what used to be the separate Builds/Moves/Team Cores tabs into
  // one Pokémon-centric view (dashboard "combine build + moves page per
  // Pokémon" ask), plus a Profile sub-section (base stats, speed tier,
  // curated archetype tags) so there's one place to see everything about a
  // single Pokémon instead of three tabs with independently-selected
  // Pokémon.
  function setupPokemonProfile() {
    var profileRows = marts.pokemon_champions_profile || [];
    var buildRows = marts.pokemon_build_usage || [];
    var moveRows = marts.pokemon_move_usage || [];
    var coreRows = marts.pokemon_team_core_usage || [];
    var archetypeRows = marts.pokemon_archetype_usage || [];

    var archetypesByPokemon = {};
    archetypeRows.forEach(function (r) {
      (archetypesByPokemon[r.pokemon_key] = archetypesByPokemon[r.pokemon_key] || []).push(
        r.archetype_name
      );
    });

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
    var buildTable = document.getElementById("build-table");
    var moveList = document.getElementById("move-ranked-list");
    var coreList = document.getElementById("team-core-ranked-list");

    var buildSortable = buildTable
      ? makeSortableTable(
          buildTable,
          [],
          function (r) {
            return (
              "<td>" + itemCell(r.item_name) + "</td>" +
              "<td>" + (r.ability ? escapeHtml(r.ability) : "—") + "</td>" +
              "<td>" + formatPercent(r.build_share) + "</td>"
            );
          },
          { defaultKey: "build_share" }
        )
      : null;

    function render(chosenName) {
      var profile = sortedProfiles.filter(function (r) {
        return r.pokemon_name === chosenName;
      })[0];

      if (statsEl) {
        if (!profile) {
          statsEl.textContent = "Select a Pokémon to see its profile.";
        } else {
          var tags = (archetypesByPokemon[profile.pokemon_key] || [])
            .map(function (name) {
              return '<span class="badge badge-rank">' + escapeHtml(name) + "</span>";
            })
            .join(" ");
          statsEl.innerHTML =
            '<div class="cell-with-icon">' +
            spriteImg(profile.pokemon_key, ICON_SIZES.lg) +
            "<div><strong>" + escapeHtml(profile.pokemon_name) + "</strong> " +
            speedTierBadge(profile.speed) + "<br>" +
            "HP " + profile.hp + " · Atk " + profile.attack + " · Def " + profile.defense +
            " · SpA " + profile.sp_attack + " · SpD " + profile.sp_defense +
            " · Spe " + profile.speed + "<br>" +
            formatPercent(profile.usage_share) + " usage · " + formatPercent(profile.win_rate) +
            " win rate" + (tags ? "<br>" + tags : "") + "</div></div>";
        }
      }

      var builds = chosenName
        ? buildRows
            .filter(function (r) {
              return r.pokemon_name === chosenName;
            })
            .sort(function (a, b) {
              return a.usage_rank - b.usage_rank;
            })
        : [];
      if (buildSortable) buildSortable.setRows(builds);

      var moves = chosenName
        ? moveRows
            .filter(function (r) {
              return r.pokemon_name === chosenName;
            })
            .sort(function (a, b) {
              return a.usage_rank - b.usage_rank;
            })
        : [];
      renderRankedList(moveList, moves, {
        iconFn: function (r) {
          return typeIcons[moveTypes[r.move_name]];
        },
        labelFn: function (r) {
          return r.move_name;
        },
        valueFn: function (r) {
          return (r.move_share || 0) * 100;
        },
        displayFn: function (r) {
          return formatPercent(r.move_share);
        },
      });

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
      renderRankedList(coreList, cores, {
        keyFn: function (r) {
          return r.partner_pokemon_key;
        },
        labelFn: function (r) {
          return r.partner_pokemon_name;
        },
        valueFn: function (r) {
          return (r.partner_share || 0) * 100;
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
  }

  // Archetype Explorer (dashboard "show competitive archetypes" ask):
  // curated groupings (dbt/seeds/archetype_pokemon_map.csv), NOT sourced
  // tournament data — see the disclaimer copy in index.html.jinja.
  function setupArchetypes() {
    var summaryRows = marts.archetype_summary || [];
    var memberRows = marts.pokemon_archetype_usage || [];
    var grid = document.getElementById("archetype-grid");
    var heading = document.getElementById("archetype-members-heading");
    var membersTable = document.getElementById("archetype-members-table");
    if (!grid) return;

    var membersSortable = membersTable
      ? makeSortableTable(
          membersTable,
          [],
          function (r) {
            return (
              '<td><span class="badge badge-rank">#' + r.member_rank + "</span></td>" +
              "<td>" + pokemonCell(r.pokemon_key, r.pokemon_name) + "</td>" +
              "<td>" + formatPercent(r.usage_share) + "</td>" +
              "<td>" + formatPercent(r.win_rate) + "</td>"
            );
          },
          { defaultKey: "usage_share" }
        )
      : null;

    grid.innerHTML = "";
    if (!summaryRows.length) {
      grid.innerHTML = '<p class="empty-state">No archetypes curated yet.</p>';
      return;
    }

    var cards = [];
    summaryRows.forEach(function (archetype) {
      var members = memberRows
        .filter(function (r) {
          return r.archetype_key === archetype.archetype_key;
        })
        .sort(function (a, b) {
          return a.member_rank - b.member_rank;
        });
      var topMembers = members.slice(0, 3);
      var card = document.createElement("button");
      card.type = "button";
      card.className = "archetype-card";
      card.setAttribute("aria-pressed", "false");
      card.innerHTML =
        "<h3>" + escapeHtml(archetype.archetype_name) + "</h3>" +
        '<div class="archetype-stats">' + archetype.member_count + " members · " +
        formatPercent(archetype.combined_usage_share) + " combined usage · " +
        formatPercent(archetype.avg_win_rate) + " avg win rate</div>" +
        '<div class="archetype-members">' +
        topMembers
          .map(function (r) {
            return sprites[r.pokemon_key] ? '<img src="' + sprites[r.pokemon_key] + '" alt="">' : "";
          })
          .join("") +
        "</div>";
      card.addEventListener("click", function () {
        cards.forEach(function (c) {
          c.setAttribute("aria-pressed", "false");
        });
        card.setAttribute("aria-pressed", "true");
        if (heading) heading.style.display = "";
        if (membersTable) membersTable.style.display = "";
        if (membersSortable) membersSortable.setRows(members);
      });
      cards.push(card);
      grid.appendChild(card);
    });

    if (cards.length) cards[0].click();
  }

  // Regulation Comparison (dashboard "assume cumulative" ask): shows both
  // the independent and cumulative legal-pool size per regulation, plus a
  // delta vs. the previous regulation, with the no-removal-signal caveat
  // as visible copy in the template (not just a code comment).
  function setupRegulations() {
    var rows = marts.legality_summary_by_regulation || [];
    var latest = DATA.kpis && DATA.kpis.latest_snapshot_date;
    var filtered = rows
      .filter(function (r) {
        return r.snapshot_date === latest;
      })
      .sort(function (a, b) {
        return a.regulation_code < b.regulation_code ? -1 : a.regulation_code > b.regulation_code ? 1 : 0;
      });
    var tbody = document.querySelector("#regulation-comparison-table tbody");
    if (!tbody) return;
    renderRows(tbody, filtered, function (r, i) {
      var prev = filtered[i - 1];
      var delta = prev ? r.cumulative_legal_pokemon_count - prev.cumulative_legal_pokemon_count : null;
      return (
        "<td>" + escapeHtml(r.regulation_code) + "</td>" +
        "<td>" + r.legal_pokemon_count + "</td>" +
        "<td>" + r.cumulative_legal_pokemon_count + "</td>" +
        "<td>" + (delta === null ? "—" : (delta >= 0 ? "+" : "") + delta) + "</td>"
      );
    });
  }

  function setupSpeedTiers() {
    var rows = (marts.pokemon_champions_profile || []).slice().sort(function (a, b) {
      return b.speed - a.speed;
    });
    var top = rows.slice(0, 20);

    renderRankedList(document.getElementById("speed-ranked-list"), top, {
      keyFn: function (r) {
        return r.pokemon_key;
      },
      labelFn: function (r) {
        return r.pokemon_name;
      },
      valueFn: function (r) {
        return r.speed;
      },
      displayFn: function (r) {
        return String(r.speed);
      },
    });

    var table = document.getElementById("speed-tiers-table");
    if (table) {
      makeSortableTable(
        table,
        rows,
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
      );
    }
  }

  // Pro Team Gallery (dashboard "team builder + previous competitive
  // screenshot" ask, part b): pre-rendered real-team cards, curated and
  // built ahead of time via `render-card` (see docs/dashboard.md), not
  // generated in the browser. Visually and functionally distinct from the
  // roster planner above it in the same tab — never itself called "Team
  // Builder" to avoid confusion with that existing feature.
  function renderProTeamGallery(addToTeamFn) {
    var container = document.getElementById("pro-team-gallery");
    if (!container) return;
    var teams = DATA.reference_teams || [];
    container.innerHTML = "";
    if (!teams.length) {
      container.innerHTML = '<p class="empty-state">No reference teams curated yet.</p>';
      return;
    }
    teams.forEach(function (team) {
      var card = document.createElement("div");
      card.className = "gallery-card";
      var img = team.card_image
        ? '<img class="gallery-card-image" src="' + team.card_image + '" alt="">'
        : "";
      var keys = team.pokemon_keys || [];
      card.innerHTML =
        img +
        '<div class="gallery-card-body">' +
        '<div class="gallery-card-player">' + escapeHtml(team.player_name || "Unknown player") +
        (team.country ? " (" + escapeHtml(team.country) + ")" : "") + "</div>" +
        '<div class="gallery-card-meta">' + escapeHtml(team.event_name || "") +
        (team.placement ? " · #" + team.placement : "") +
        (team.archetype_key ? " · " + escapeHtml(team.archetype_key) : "") + "</div>" +
        '<button class="btn btn-sm" type="button"' + (keys.length ? "" : " disabled") +
        ">Load into my builder</button></div>";
      var btn = card.querySelector("button");
      if (btn && keys.length) {
        btn.addEventListener("click", function () {
          keys.forEach(function (key) {
            addToTeamFn(key);
          });
        });
      }
      container.appendChild(card);
    });
  }

  // Fully client-side (no backend): lets a visitor assemble a roster of up
  // to 6 from the current legal pool (pokemon_champions_profile), ordered
  // by usage/win-rate/speed per docs/design-system.md's ordering
  // convention, and see their picks' speed order — reusing the same
  // speed-tier bucketing as the Speed Tiers tab. Persisted to
  // localStorage only; never sent anywhere. The Pro Team Gallery below it
  // is a separate, read-only reference feature (see renderProTeamGallery).
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
      team = saved
        .filter(function (key) {
          return byKey[key];
        })
        .slice(0, MAX_TEAM_SIZE);
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
      if (team.length >= MAX_TEAM_SIZE || team.indexOf(key) !== -1 || !byKey[key]) return;
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
          spriteImg(r.pokemon_key, ICON_SIZES.md) +
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
          spriteImg(r.pokemon_key, ICON_SIZES.sm) +
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
    renderProTeamGallery(addToTeam);
  }

  var tabInitializers = {
    overview: setupOverview,
    usage: setupUsage,
    "pokemon-profile": setupPokemonProfile,
    archetypes: setupArchetypes,
    regulations: setupRegulations,
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
