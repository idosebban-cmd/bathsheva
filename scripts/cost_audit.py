"""Write docs/cost-assumptions-audit.md for a fresh, default Faro project.

Usage (from the repo root): backend/.venv/bin/python scripts/cost_audit.py
Uses a temporary database, so it reflects the seed data and template only.
"""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ["WORKBENCH_DATA_DIR"] = tempfile.mkdtemp(prefix="cost-audit-")
os.environ.setdefault("WORKBENCH_LLM_PROVIDER", "none")
sys.path.insert(0, str(ROOT / "backend"))
os.chdir(ROOT / "backend")

from app.config import settings  # noqa: E402
from app.db import init_db, new_session  # noqa: E402
from app.services.cost_audit import audit_markdown, cost_audit  # noqa: E402
from app.services.projects import create_project  # noqa: E402

init_db(settings.database_url)
session = new_session()
project = create_project(session, "Faro", template="faro")
audit = cost_audit(session, project)
out = ROOT / "docs" / "cost-assumptions-audit.md"
out.parent.mkdir(exist_ok=True)
out.write_text(audit_markdown(audit))
print(f"Wrote {out.relative_to(ROOT)}: {len(audit['rows'])} values, unit cost £{audit['unit_cost_mid']:.2f} at {audit['quantity']}")
for r in audit["rows"][:5]:
    print(f"  {r['rank']}. {r['label']}: ±£{abs(r['swing']):.2f} ({abs(r['swing_pct']):.1f}%)")
