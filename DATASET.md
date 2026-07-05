## V1 selected source scope

To deliver the first usable dataset artifact with manageable complexity, the v1
build scope is limited to:

1. **PokéAPI** (canonical baseline)
2. **OP.GG Pokémon Champions** (format-specific legal pool and stat changes)
3. **MunchStats** (tournament and roster usage records)

Other listed sources remain important for future phases, but are out of v1
ingestion scope until the core schema and refresh pipeline stabilize.

## 1. PokéAPI Raw CSV Backends
**Best for:** Raw, unmodified game data and canonical Pokédex information

PokéAPI maintains a complete, community-curated database of all official Pokémon game data in raw CSV format. This includes base stats, type matchups, generational information, move mechanics, physical attributes, and item catalogs. This is your canonical source for the standard game ruleset before any competitive modifications.

**Key assets:**
- Master Database (including csvs, sprites, cries): [pokeapi/data/v2/](https://github.com/PokeAPI/pokeapi/tree/master/data/v2)
- Master Species Base Stats: [pokemon_stats.csv](https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/pokemon_stats.csv)
- Move Pool Master Index: [moves.csv](https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/moves.csv)
- Items Master Index: [items.csv](https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/items.csv)

**How to extract:**
1. Browse the full repository at [github.com/PokeAPI/pokeapi/tree/master/data/v2/csv](https://github.com/PokeAPI/pokeapi/tree/master/data/v2/csv)
2. Copy raw file URLs and import directly into Python (pd.read_csv), Google Sheets, or Excel
3. Link updates automatically if you reference the raw URL

## 2. OP.GG Pokémon Champions
**Best for:** Competitive legal pool, rebalanced base stats, and custom mechanics

OP.GG serves as the authoritative source for the Pokémon Champions tier—a curated competitive format featuring custom base stat rebalances, custom Mega Evolutions, and a restricted 317-entry legal Pokédex. Use this to align your competitive analysis with the exact rules and statistics that apply in tournaments.

**Key coverage:**
- Legally playable Pokémon (317-entry restricted pool)
- Custom base stats (modified from official values)
- Custom Mega Evolution forms and stats
- Tier-specific items and ability adjustments

**How to extract:**
1. Visit [op.gg/pokemon-champions/pokedex](https://op.gg/pokemon-champions/pokedex)
2. Use a browser scraper (e.g., Selenium, Puppeteer) or table capture extension
3. Extract the full Pokédex grid with custom stats
4. Join with PokéAPI canonical data via numeric ID to identify what was changed

## 3. PokéBase App
**Best for:** Competitive regulation rules, banned/restricted Pokémon, and official speed tiers

PokéBase aggregates competitive-specific ruleset information for Pokémon Champions, including which Pokémon are legal in each regulation, custom tier assignments, and critical speed tier breakpoints. This source reflects the actual competitive metagame restrictions that differ from the base game.

**Key coverage:**
- Legal Pokémon by regulation bracket
- Speed tier classifications
- Item restrictions and custom allowances
- Mega Evolution availability

**How to extract:**
1. Visit [pokebase.app/pokemon-champions/pokemon](https://pokebase.app/pokemon-champions/pokemon)
2. Copy the data tables from each regulation panel
3. Paste into Excel or Google Sheets for CSV conversion
4. Optionally use browser table export extensions for automation

## 4. MunchStats
**Best for:** Live tournament results and player roster data

MunchStats bridges static Pokédex data with active competitive tournament metadata by scraping RK9.gg tournament pairings and results. Use this to track what Pokémon were actually used in recent competitions and which teams are meta-relevant.

**Key coverage:**
- Player rosters from recent tournaments
- Team compositions and move combinations
- Tournament standings and placement data
- Current metagame trends

**How to extract:**
1. Pull structured JSON from [github.com/PizzaTimeJoshua/munchstats](https://github.com/PizzaTimeJoshua/munchstats)
2. Use Python: `pd.read_json(url)` or [convert.town JSON-to-CSV](https://convert.town/json-to-csv)
3. Flatten nested team arrays into flat rows (one row per team member)

## 5. Limitless VGC
**Best for:** Historical tournament brackets, player win rates, and macro competitive statistics

Limitless archives grassroots and official VGC event brackets, providing a comprehensive history of tournament placements, player performance metrics, and macro-level competitive trends across regions.

**Key coverage:**
- Tournament brackets and standings by event
- Player historical records and win rates
- Regional and national competition data
- Historical metagame snapshots

**How to extract:**
1. Navigate to their historical brackets page
2. Use a browser table extraction tool (e.g., Table Capture extension) to screenshot tables
3. Convert to CSV format and import into your analysis pipeline
4. Alternatively, contact Limitless for bulk data exports if available

## 6. Victory Road
**Best for:** Certified champion team building, detailed EV spreads, and verified movesets

Victory Road archives complete team slates from certified tournament champions, including full team compositions, EV distributions, item assignments, and move choices. This is the most detailed source for understanding how top players actually built their championship teams.

**Key coverage:**
- Complete team roster with all 6 Pokémon
- Exact EV and IV spreads per Pokémon
- Move and item choices for each team member
- Tournament context and placement

**How to extract:**
1. Browse [victory-road.com](https://victory-road.com) or similar archives
2. Export teams using their "Showdown Paste" format
3. Feed paste data into a Python string parser to convert to tabular format:
   - Example: Split on newlines, extract Pokémon names, stats, moves, items
4. Store in CSV with schema: `pokemon_id | pokemon_name | evs | moveset | item | team_id`