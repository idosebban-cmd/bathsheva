"""External quotes: comparison against workbench estimates, and the quoting pack export.

Quotes are for the user to review. Nothing here writes to the rules engine or
seed data.
"""

from __future__ import annotations

import io
import re
import zipfile
from datetime import datetime, timezone
from typing import Any, Callable

from app.config import settings
from app.models import ExternalQuote, Part, Project
from app.services.bom import build_bom
from app.services.cad import latest_model

ESTIMATE_CURRENCY = "GBP"


def manual_estimate(part: Part) -> dict[str, Any] | None:
    """The unit cost range typed on the part (Parts / BOM), if set."""
    if part.cost_low is None and part.cost_high is None:
        return None
    low = part.cost_low if part.cost_low is not None else part.cost_high
    high = part.cost_high if part.cost_high is not None else part.cost_low
    low, high = min(low, high), max(low, high)
    return {"low": low, "high": high, "currency": ESTIMATE_CURRENCY,
            "basis": "Unit cost estimate on the part (Parts / BOM)", "source": "manual"}


def estimate_for(part: Part, model_estimate: Callable[[float], dict[str, Any] | None] | None = None,
                 quantity: float | None = None) -> dict[str, Any] | None:
    """Manual estimate if set (it always wins), else the cost model's range at `quantity` pieces."""
    manual = manual_estimate(part)
    if manual is not None or model_estimate is None or quantity is None:
        return manual
    return model_estimate(quantity)


def compare(estimate: dict[str, Any] | None, unit_price: float, currency: str) -> dict[str, Any]:
    """How a quoted unit price sits against the estimate range.

    status: no_estimate | currency_mismatch | below | within | above.
    diff is measured from the nearest end of the range (0 when within).
    """
    if estimate is None:
        return {"status": "no_estimate", "diff": None, "diff_pct": None,
                "text": "No workbench estimate for this part yet."}
    if currency.upper() != estimate["currency"]:
        return {"status": "currency_mismatch", "diff": None, "diff_pct": None,
                "text": f"Quote is in {currency.upper()}, estimate is in {estimate['currency']}; not compared."}
    low, high = estimate["low"], estimate["high"]
    if unit_price < low:
        diff = unit_price - low
        pct = diff / low * 100 if low else None
        status = "below"
    elif unit_price > high:
        diff = unit_price - high
        pct = diff / high * 100 if high else None
        status = "above"
    else:
        return {"status": "within", "diff": 0.0, "diff_pct": 0.0, "text": "Within the estimate range."}
    pct_text = f" ({pct:+.0f}%)" if pct is not None else ""
    edge = "low" if status == "below" else "high"
    return {
        "status": status,
        "diff": round(diff, 2),
        "diff_pct": round(pct, 1) if pct is not None else None,
        "text": f"{abs(diff):.2f} {currency.upper()} {status} the estimate's {edge} end{pct_text}.",
    }


def quote_dict(q: ExternalQuote, estimate: dict[str, Any] | None, revision_number: int | None) -> dict[str, Any]:
    return {
        "id": q.id,
        "part_id": q.part_id,
        "revision_id": q.revision_id,
        "revision_number": revision_number,
        "source": q.source,
        "quote_date": q.quote_date.isoformat(),
        "process": q.process,
        "material": q.material,
        "finish": q.finish,
        "quantity": q.quantity,
        "unit_price": q.unit_price,
        "currency": q.currency,
        "total_price": round(q.unit_price * q.quantity, 2),
        "lead_time_days": q.lead_time_days,
        "dfm_notes": q.dfm_notes,
        "attachment_path": q.attachment_path,
        "attachment_filename": q.attachment_filename,
        "created_at": q.created_at.isoformat(),
        "comparison": compare(estimate, q.unit_price, q.currency),
    }


# ---------------------------------------------------------------------------
# Quoting pack
# ---------------------------------------------------------------------------


class QuotePackError(ValueError):
    pass


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_") or "part"


def build_quote_pack(project: Project) -> tuple[str, bytes]:
    """Zip of each manufactured part's STEP file (named by part) plus a README from the BOM.

    Bought-in parts (and derived hardware) are listed in the README but get no STEP:
    their CAD bodies are placeholders, not designs to quote.
    """
    model = latest_model(project)
    if model is None:
        raise QuotePackError("Generate CAD first: the quoting pack uses the latest CAD version's STEP files.")
    steps = {o.part_key: o.path for o in model.outputs if o.format == "step" and o.part_key}
    bom = build_bom(project)

    included: list[tuple[dict[str, Any], str]] = []
    not_included: list[tuple[dict[str, Any], str]] = []
    used_names: set[str] = set()
    for row in bom["rows"]:
        if row["derived"]:
            not_included.append((row, "bought-in hardware"))
            continue
        bought_in = "bought-in" in (row["process"] or "").lower()
        step = steps.get(row["cad_key"] or "")
        if bought_in:
            not_included.append((row, "bought-in component (CAD body is a placeholder)"))
        elif step is None:
            not_included.append((row, "no CAD body"))
        else:
            name = f"{int(row['item']):02d}_{_slug(row['name'])}.step"
            while name in used_names:
                name = name.replace(".step", "_x.step")
            used_names.add(name)
            included.append((row, name))
            row["_step"] = step

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# {project.name}: parts for quoting",
        "",
        f"CAD version v{model.version} · generated {generated} by Product Workbench.",
        "Units: millimetres. One STEP file per part.",
        "",
        "Material and process marked *(recommended)* are the workbench's unverified suggestions, not decisions.",
        "Please quote the stated quantity and tell us about any DFM concerns.",
        "",
        "## Parts to quote",
        "",
        "| File | Part | Qty | Material | Process | Finish | Size (mm) |",
        "|---|---|---|---|---|---|---|",
    ]
    for row, fname in included:
        tag = "" if row["status"] == "decided" else " *(recommended)*"
        lines.append(
            f"| {fname} | {row['name']} | {row['quantity']} | {row['material'] or 'TBD'}{tag} | "
            f"{row['process'] or 'TBD'}{tag} | {row['finish'] or 'TBD'} | {row['size_mm'] or ''} |"
        )
    if not included:
        lines.append("| (none) | | | | | | |")
    if not_included:
        lines += ["", "## Not included", ""]
        for row, why in not_included:
            lines.append(f"- {row['name']} × {row['quantity']}: {why}")
    readme = "\n".join(lines) + "\n"

    buf = io.BytesIO()
    folder = f"{project.slug}_quote_pack_v{model.version}"
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{folder}/README.md", readme)
        for row, fname in included:
            zf.write(settings.data_dir / row["_step"], f"{folder}/{fname}")
    return f"{folder}.zip", buf.getvalue()
