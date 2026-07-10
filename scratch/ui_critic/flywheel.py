"""Quality Flywheel: build each A2UI screen -> render headlessly -> vision-critique -> report.

Run:  uv run --with playwright python scratch/ui_critic/flywheel.py
Outputs PNGs in scratch/ui_critic/shots/ and markdown reports in scratch/ui_critic/reports/.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)   # render, critic
sys.path.insert(0, REPO)   # app.*

import render  # noqa: E402
import critic  # noqa: E402
from app import tools  # noqa: E402

SHOTS = os.path.join(HERE, "shots")
REPORTS = os.path.join(HERE, "reports")

# Synthetic fallback data so the flywheel runs even without BigQuery access.
FAKE_INVENTORY = [
    {"product_id": "halloween_costume", "received": 900, "sold": 800, "current_stock": 100, "status": "Low Stock (Season Coming)"},
    {"product_id": "halloween_skeleton", "received": 300, "sold": 280, "current_stock": 20, "status": "Low Stock (Season Coming)"},
    {"product_id": "party_balloons", "received": 500, "sold": 120, "current_stock": 380, "status": "Good"},
    {"product_id": "birthday_candles", "received": 400, "sold": 90, "current_stock": 310, "status": "Good"},
]
FAKE_HISTORY = [
    {"date": "2025-08", "sales": 120, "type": "actual"}, {"date": "2025-09", "sales": 240, "type": "actual"},
    {"date": "2025-10", "sales": 780, "type": "actual"}, {"date": "2025-11", "sales": 210, "type": "actual"},
    {"date": "2026-05", "sales": 90, "type": "actual"}, {"date": "2026-06", "sales": 110, "type": "actual"},
]
FAKE_FORECAST = [
    {"date": "2026-07", "sales": 130, "type": "forecast"}, {"date": "2026-08", "sales": 180, "type": "forecast"},
    {"date": "2026-09", "sales": 264, "type": "forecast"}, {"date": "2026-10", "sales": 858, "type": "forecast"},
    {"date": "2026-11", "sales": 230, "type": "forecast"}, {"date": "2026-12", "sales": 140, "type": "forecast"},
]

DIMS = ["visual_hierarchy", "brand_cohesion", "color_contrast", "info_density",
        "delight_wow", "chart_quality", "readability", "cta_clarity"]


def _payloads():
    """Real data via BigQuery if available; otherwise synthetic."""
    try:
        inv = tools.query_inventory_status()
        inv_p = inv["a2ui_payload"] if inv.get("status") == "success" else tools.build_inventory_payload(FAKE_INVENTORY)
        fc = tools.get_sales_forecast("halloween_costume")
        fc_p = fc["a2ui_payload"] if fc.get("status") == "success" else tools.build_forecast_payload("halloween_costume", FAKE_HISTORY, FAKE_FORECAST)
    except Exception as e:  # noqa: BLE001
        print(f"--- BigQuery unavailable ({e}); using synthetic data ---")
        inv_p = tools.build_inventory_payload(FAKE_INVENTORY)
        fc_p = tools.build_forecast_payload("halloween_costume", FAKE_HISTORY, FAKE_FORECAST)
    po_p = tools.build_po_payload("PO-DEMO1234", "birthday_candles", 500, "2026-07-09", "2026-07-23")
    return {"inventory": inv_p, "forecast": fc_p, "purchase_order": po_p}


# Native buttons rendered below each panel (not in the screenshot) — given to the critic for fair CTA scoring.
CTAS = {
    "inventory": ["📈 View Skeleton Decor Forecast (context-aware to the lowest-stock item)"],
    "forecast": ["🛒 Order 500 more Halloween Costume", "🏠 Back to Inventory"],
    "purchase_order": ["🏠 Back to Inventory"],
}


def _write_report(name, png, c):
    os.makedirs(REPORTS, exist_ok=True)
    lines = [f"# UI critique — {name}", "", f"![shot]({os.path.relpath(png, REPORTS)})", "",
             f"**Overall: {c.overall}/5** — {c.verdict}", "", "## Scores"]
    lines += [f"- {d}: {getattr(c, d)}/5" for d in DIMS]
    lines += ["", "## Strengths"] + [f"- {s}" for s in c.strengths]
    lines += ["", "## Top fixes"] + [f"{i}. {fx}" for i, fx in enumerate(c.top_fixes, 1)]
    path = os.path.join(REPORTS, f"{name}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


def main():
    payloads = _payloads()
    results = {}
    for name, payload in payloads.items():
        png = os.path.join(SHOTS, f"{name}.png")
        print(f"\n=== {name} ===")
        render.render_payload_to_png(payload, png, width=560)
        print(f"  rendered -> {png}")
        c = critic.assess(png, name, cta_labels=CTAS.get(name))
        results[name] = c
        _write_report(name, png, c)
        print(f"  overall {c.overall}/5 | " + " ".join(f"{d[:4]}={getattr(c,d)}" for d in DIMS))
        for fx in c.top_fixes:
            print(f"    fix: {fx}")

    print("\n================ SCORECARD ================")
    hdr = "screen".ljust(16) + "  " + "  ".join(d[:4] for d in DIMS) + "   overall"
    print(hdr)
    for name, c in results.items():
        row = name.ljust(16) + "  " + "  ".join(str(getattr(c, d)).rjust(4) for d in DIMS) + f"   {c.overall}"
        print(row)
    avg = sum(c.overall for c in results.values()) / max(len(results), 1)
    print(f"\nAVG overall: {avg:.2f}/5   (target: avg>=4.3, no dim<4)")


if __name__ == "__main__":
    main()
