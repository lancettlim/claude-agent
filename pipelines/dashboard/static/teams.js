/* Team Builder + Top Teams tabs (docs/design-system.md's "Team card /
 * pokepaste component", "Top Teams tab"). Loaded after app.js/matchup.js
 * and reuses window.DashboardApp for data/helpers rather than duplicating
 * them.
 *
 * Team Builder and Top Teams share one addToTeam/team-state pipeline (a
 * pokepaste import or a Pro Team Gallery "Load into my builder" click both
 * need to push Pokémon into the same saved team, regardless of which tab
 * the visitor is on when they do it) — see ensureTeamBuilder() below for
 * how that stays correct even if Top Teams is visited before Team Builder
 * ever wires up its DOM (tabs otherwise init lazily, on first activation). */
(function () {
  "use strict";

  var App = window.DashboardApp;
  if (!App) return;

  var marts = App.marts;
  var sprites = App.sprites;

  function groupByPokemonKey(rows) {
    var out = {};
    (rows || []).forEach(function (r) {
      (out[r.pokemon_key] = out[r.pokemon_key] || []).push(r);
    });
    return out;
  }

  function sortByUsageRank(rows) {
    return (rows || []).slice().sort(function (a, b) {
      return a.usage_rank - b.usage_rank;
    });
  }

  // ---------- pokepaste (Showdown-export-text) import/export ----------
  // "Do it like vgcpastes/pokepaste": accepts the same plain-text format
  // pokepast.es itself accepts (species [@ item] / Ability: .../ moves),
  // parsed client-side — there's no live URL fetch (static site, no
  // backend/CORS-proxy), so "paste a link" means paste the export text
  // you'd otherwise paste into pokepast.es to create one.
  function keyToShowdownName(key) {
    return key
      .split("-")
      .map(function (part) {
        return part.charAt(0).toUpperCase() + part.slice(1);
      })
      .join("-");
  }

  function buildNameLookup() {
    var lookup = {};
    Object.keys(App.pokemonNames).forEach(function (key) {
      lookup[App.pokemonNames[key].toLowerCase()] = key;
    });
    return lookup;
  }

  function normalizeSpeciesName(name) {
    return name.replace(/[-\s.']/g, "").toLowerCase();
  }

  function parsePokepaste(text) {
    var lookup = buildNameLookup();
    var blocks = text
      .split(/\n\s*\n/)
      .map(function (b) {
        return b.trim();
      })
      .filter(Boolean);
    var resolvedKeys = [];
    var unresolvedNames = [];
    blocks.forEach(function (block) {
      var firstLine = block.split("\n")[0];
      var atIndex = firstLine.indexOf(" @ ");
      var namePart = atIndex !== -1 ? firstLine.slice(0, atIndex) : firstLine;
      var parenMatch = namePart.match(/\(([^)]+)\)/);
      var species = parenMatch ? parenMatch[1] : namePart;
      species = species.replace(/\s*\((M|F)\)/g, "").trim();
      var key = lookup[normalizeSpeciesName(species)];
      if (key) {
        resolvedKeys.push(key);
      } else if (species) {
        unresolvedNames.push(species);
      }
    });
    return { resolvedKeys: resolvedKeys, unresolvedNames: unresolvedNames };
  }

  function exportTeamAsPokepaste(teamKeys) {
    var byKey = {};
    (marts.pokemon_champions_profile || []).forEach(function (r) {
      byKey[r.pokemon_key] = r;
    });
    var itemsByKey = groupByPokemonKey(marts.pokemon_item_usage);
    var abilitiesByKey = groupByPokemonKey(marts.pokemon_ability_usage);
    var movesByKey = groupByPokemonKey(marts.pokemon_move_usage);

    var blocks = teamKeys
      .map(function (key) {
        if (!byKey[key]) return null;
        var name = keyToShowdownName(key);
        var topItem = sortByUsageRank(itemsByKey[key])[0];
        var topAbility = sortByUsageRank(abilitiesByKey[key])[0];
        var topMoves = sortByUsageRank(movesByKey[key]).slice(0, 4);
        var lines = [name + (topItem ? " @ " + topItem.item_name : "")];
        if (topAbility) lines.push("Ability: " + topAbility.ability);
        topMoves.forEach(function (m) {
          lines.push("- " + m.move_name);
        });
        return lines.join("\n");
      })
      .filter(Boolean);
    return blocks.join("\n\n");
  }

  // ---------- Team Builder (fully client-side; localStorage only) ----------
  var teamBuilderState = null;

  function setupTeamBuilder() {
    var rows = marts.pokemon_champions_profile || [];
    var byKey = {};
    rows.forEach(function (r) {
      byKey[r.pokemon_key] = r;
    });
    var abilitiesByKey = groupByPokemonKey(marts.pokemon_ability_usage);
    var movesByKey = groupByPokemonKey(marts.pokemon_move_usage);

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
    var typeFilterEl = document.getElementById("team-builder-type-filter");
    var availableList = document.getElementById("team-builder-available");
    var slotsEl = document.getElementById("team-builder-slots");
    var countEl = document.getElementById("team-builder-count");
    var speedOrderEl = document.getElementById("team-builder-speed-order");
    var summaryEl = document.getElementById("team-builder-summary");
    var clearBtn = document.getElementById("team-builder-clear");
    var exportBtn = document.getElementById("team-builder-export");
    var exportOutput = document.getElementById("team-builder-export-output");
    var selectedTypes = {};

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

    function loadTeam(keys) {
      team = keys.filter(function (key) {
        return byKey[key];
      }).slice(0, MAX_TEAM_SIZE);
      persist();
      renderAll();
    }

    function renderAvailable() {
      if (!availableList) return;
      var query = ((searchInput && searchInput.value) || "").trim().toLowerCase();
      var sortBy = sortSelect ? sortSelect.value : "usage";
      var candidates = rows.filter(function (r) {
        if (team.indexOf(r.pokemon_key) !== -1) return false;
        if (r.pokemon_name.toLowerCase().indexOf(query) === -1) return false;
        if (!App.passesTypeFilter(selectedTypes, r.type_1, r.type_2)) return false;
        return true;
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
          App.spriteImg(r.pokemon_key, App.ICON_SIZES.md) +
          '<div class="roster-info"><div class="roster-name">' + App.escapeHtml(r.pokemon_name) + "</div>" +
          '<div class="roster-sub">' + App.formatPercent(r.usage_share) + " usage · " +
          App.formatPercent(r.win_rate) + " win rate · " + (r.speed != null ? r.speed : "—") + " speed</div></div>" +
          '<button class="btn btn-sm" type="button"' + (full ? " disabled" : "") + ">Add</button>";
        li.querySelector("button").addEventListener("click", function () {
          addToTeam(r.pokemon_key);
        });
        availableList.appendChild(li);
      });
      if (!candidates.length) {
        var empty = document.createElement("li");
        empty.className = "roster-item";
        empty.textContent = "No Pokémon match your search/filters.";
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
        var topAbility = sortByUsageRank(abilitiesByKey[key])[0];
        var moves = sortByUsageRank(movesByKey[key]).slice(0, 4);
        slot.className = "team-slot";
        slot.innerHTML =
          (sprites[key] ? '<img src="' + sprites[key] + '" alt="">' : "") +
          '<div class="slot-name">' + App.escapeHtml(r.pokemon_name) + "</div>" +
          '<div class="slot-detail">HP ' + r.hp + " Atk " + r.attack + " Def " + r.defense +
          " SpA " + r.sp_attack + " SpD " + r.sp_defense + " Spe " + r.speed + "</div>" +
          (topAbility ? '<div class="slot-detail">' + App.escapeHtml(topAbility.ability) + "</div>" : "") +
          (moves.length ? '<select class="slot-move-select" aria-label="Top recorded moves"></select>' : '<div class="slot-detail">No recorded moves</div>') +
          '<button class="btn-remove" type="button" aria-label="Remove ' + App.escapeHtml(r.pokemon_name) + '">Remove</button>';
        if (moves.length) {
          var select = slot.querySelector(".slot-move-select");
          moves.forEach(function (m) {
            var opt = document.createElement("option");
            opt.value = m.move_name;
            opt.textContent = m.move_name;
            select.appendChild(opt);
          });
        }
        slot.querySelector(".btn-remove").addEventListener("click", function () {
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
      if (exportBtn) exportBtn.disabled = team.length === 0;
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
          App.spriteImg(r.pokemon_key, App.ICON_SIZES.sm) +
          "<span>" + App.escapeHtml(r.pokemon_name) + "</span>" +
          App.speedTierBadge(r.speed) +
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
        '<div class="stat"><strong>' + App.formatPercent(avg("usage_share")) + "</strong>Avg. usage share</div>" +
        '<div class="stat"><strong>' + App.formatPercent(avg("win_rate")) + "</strong>Avg. win rate</div>";
    }

    function renderAll() {
      renderAvailable();
      renderSlots();
      renderSpeedOrder();
      renderSummary();
      if (exportOutput) exportOutput.style.display = "none";
    }

    if (searchInput) searchInput.addEventListener("input", renderAvailable);
    if (sortSelect) sortSelect.addEventListener("change", renderAvailable);
    App.renderTypeFilterChips(typeFilterEl, selectedTypes, renderAvailable);
    if (clearBtn) {
      clearBtn.addEventListener("click", function () {
        team = [];
        persist();
        renderAll();
      });
    }
    if (exportBtn && exportOutput) {
      exportBtn.addEventListener("click", function () {
        exportOutput.value = exportTeamAsPokepaste(team);
        exportOutput.style.display = team.length ? "block" : "none";
        if (team.length) exportOutput.select();
      });
    }

    renderAll();

    return { addToTeam: addToTeam, loadTeam: loadTeam };
  }

  // Team Builder normally initializes lazily (on first tab activation,
  // like every other tab) — but a Top Teams pokepaste import or gallery
  // "Load into my builder" click can happen before that, so both paths
  // call this instead of the raw team-builder state, forcing init on
  // first use rather than assuming the tab was already visited.
  function ensureTeamBuilder() {
    if (!teamBuilderState) teamBuilderState = setupTeamBuilder();
    return teamBuilderState;
  }

  // ---------- Pro Team Gallery (curated real-team reference cards) ----------
  function renderProTeamGallery() {
    var container = document.getElementById("pro-team-gallery");
    if (!container) return;
    var teams = App.DATA.reference_teams || [];
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
        '<div class="gallery-card-player">' + App.escapeHtml(team.player_name || "Unknown player") +
        (team.country ? " (" + App.escapeHtml(team.country) + ")" : "") + "</div>" +
        '<div class="gallery-card-meta">' + App.escapeHtml(team.event_name || "") +
        (team.placement ? " · #" + team.placement : "") +
        (team.archetype_key ? " · " + App.escapeHtml(team.archetype_key) : "") + "</div>" +
        '<button class="btn btn-sm" type="button"' + (keys.length ? "" : " disabled") +
        ">Load into my builder</button></div>";
      var btn = card.querySelector("button");
      if (btn && keys.length) {
        btn.addEventListener("click", function () {
          var state = ensureTeamBuilder();
          keys.forEach(function (key) {
            state.addToTeam(key);
          });
        });
      }
      container.appendChild(card);
    });
  }

  // ---------- Top Teams tab: real leaderboard + pokepaste import + gallery ----------
  function setupTopTeams() {
    var teamRows = marts.top_tournament_teams || [];
    var grid = document.getElementById("top-teams-grid");
    if (grid) {
      var ranked = teamRows.slice().sort(function (a, b) {
        return a.team_rank - b.team_rank;
      });
      App.renderGrid6xn(grid, ranked.slice(0, 18), {
        iconFn: function (r) {
          var firstKey = (r.pokemon_keys || "").split("|")[0];
          return sprites[firstKey];
        },
        labelFn: function (r) {
          return (r.player_name || "Unknown") + (r.event_name ? " · " + r.event_name : "");
        },
        displayFn: function (r) {
          return App.formatPercent(r.win_rate);
        },
        subFn: function (r) {
          var names = (r.pokemon_keys || "")
            .split("|")
            .map(function (key) {
              return App.pokemonNames[key] || key;
            })
            .join(", ");
          return names;
        },
      });
    }

    var input = document.getElementById("pokepaste-input");
    var loadBtn = document.getElementById("pokepaste-load");
    var statusEl = document.getElementById("pokepaste-status");
    if (loadBtn && input) {
      loadBtn.addEventListener("click", function () {
        var parsed = parsePokepaste(input.value || "");
        if (!parsed.resolvedKeys.length) {
          if (statusEl) statusEl.textContent = "No recognizable Pokémon found in that paste.";
          return;
        }
        ensureTeamBuilder().loadTeam(parsed.resolvedKeys);
        if (statusEl) {
          statusEl.textContent =
            "Loaded " + parsed.resolvedKeys.length + " Pokémon into Team Builder" +
            (parsed.unresolvedNames.length
              ? " (" + parsed.unresolvedNames.length + " not recognized: " + parsed.unresolvedNames.join(", ") + ")"
              : ".");
        }
      });
    }

    renderProTeamGallery();
  }

  App.registerTab("team-builder", function () {
    ensureTeamBuilder();
  });
  App.registerTab("top-teams", setupTopTeams);
})();
