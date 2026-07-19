"""dashboard/ isn't a Python package (both dashboard scripts run standalone
via `uv run streamlit run` / `uv run python`, which puts dashboard/ on
sys.path[0] for their own same-directory imports) — add it to sys.path
here so tests can `import game_data` the same way.
"""

import sys
from pathlib import Path

DASHBOARD_DIR = Path(__file__).resolve().parents[3] / "dashboard"
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))
