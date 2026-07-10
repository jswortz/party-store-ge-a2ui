# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Festive & premium A2UI screen builder for the Party Store demo.

Native A2UI has almost no styling (Text usageHint only; Card is a bare box; no color/gradient). So each
screen is ONE branded ``WebFrameSrcdoc`` HTML panel (rich, self-contained, renders in GE's side canvas)
plus native A2UI Buttons for interactivity. This mirrors the proven pattern in
rag_pg_ip/pg_razor_agent/ui_builder.py; the executor wraps each returned command dict in a DataPart
tagged ``mimeType=application/json+a2ui``.

Charts are inline SVG (no external JS) so they render identically in the headless critic and in GE.
"""
from __future__ import annotations

import html
import math
from typing import Any, Dict, List

# --- Festive-premium theme -------------------------------------------------
BRAND = "Party Store"
HERO_GRADIENT = "linear-gradient(120deg,#7C3AED 0%,#DB2777 55%,#06B6D4 100%)"
INK = "#0b1020"
MUTED = "#4a5468"          # darker secondary text for contrast
SUCCESS = "#0ea371"
WARNING = "#d97706"
DANGER = "#e11d48"
ACCENT = "#7C3AED"
ACCENT2 = "#DB2777"

# product_id -> display metadata (name, emoji, nominal unit price for the value KPI)
PRODUCT_META: Dict[str, Dict[str, Any]] = {
    "halloween_costume": {"name": "Halloween Costume", "emoji": "🎃", "price": 24.99},
    "halloween_skeleton": {"name": "Skeleton Decor", "emoji": "💀", "price": 39.99},
    "party_balloons": {"name": "Party Balloons", "emoji": "🎈", "price": 6.99},
    "birthday_candles": {"name": "Birthday Candles", "emoji": "🎂", "price": 3.99},
}


def product_meta(pid: str) -> Dict[str, Any]:
    if pid in PRODUCT_META:
        return PRODUCT_META[pid]
    name = " ".join(w.capitalize() for w in (pid or "").replace("_", " ").split())
    return {"name": name or "Product", "emoji": "🎉", "price": 9.99}


def _sev(item: Dict[str, Any]) -> str:
    """Severity bucket for an inventory item -> good | warn | crit."""
    stock = item.get("current_stock", 0)
    if stock < 25:
        return "crit"
    if "Low" in (item.get("status") or ""):
        return "warn"
    return "good"


_SEV_COLOR = {"good": SUCCESS, "warn": WARNING, "crit": DANGER}
_SEV_LABEL = {"good": "Healthy", "warn": "Low Stock", "crit": "Critical"}
NEUTRAL = "#64748b"       # non-status KPI accent (reserve red/amber/green for status)


def _target_stock(pid: str) -> int:
    """Healthy target stock per product (2x the reorder threshold) so the bar is meaningful."""
    return 400 if pid in ("halloween_costume", "halloween_skeleton") else 150


def most_at_risk_seasonal(inventory: List[Dict[str, Any]]) -> str:
    """product_id of the lowest-stock seasonal item (for a context-aware forecast CTA)."""
    seasonal = [i for i in inventory if i["product_id"] in ("halloween_costume", "halloween_skeleton")]
    if not seasonal:
        return "halloween_costume"
    return min(seasonal, key=lambda i: i.get("current_stock", 0))["product_id"]


# --- shared HTML chrome ----------------------------------------------------
def _doc_head(extra_css: str = "") -> str:
    return f"""<!doctype html><html><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<link rel='preconnect' href='https://fonts.googleapis.com'>
<link href='https://fonts.googleapis.com/css2?family=Outfit:wght@500;700;800&family=Inter:wght@400;500;600;700&display=swap' rel='stylesheet'>
<style>
*{{box-sizing:border-box}}
html,body{{margin:0;background:#eef1f8;color:{INK};
font-family:'Inter',-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased}}
.wrap{{max-width:560px;margin:0 auto;padding:13px}}
.hero{{position:relative;overflow:hidden;border-radius:18px;padding:14px 18px 15px;color:#fff;
background:{HERO_GRADIENT};box-shadow:0 12px 30px -12px rgba(124,58,237,.55)}}
.hero::after{{content:'';position:absolute;right:-38px;top:-46px;width:150px;height:150px;border-radius:50%;
background:rgba(255,255,255,.13)}}
.hero .chip{{font-family:'Outfit';font-weight:800;font-size:14px;background:rgba(255,255,255,.24);
padding:4px 10px;border-radius:9px;display:inline-block}}
.hero .approved{{position:absolute;top:13px;right:15px;background:rgba(255,255,255,.94);color:{SUCCESS};
font-family:'Outfit';font-weight:800;font-size:12px;letter-spacing:.05em;padding:6px 12px;border-radius:999px;
box-shadow:0 5px 14px -5px rgba(0,0,0,.35);z-index:2;animation:pop .5s ease-out}}
@keyframes pop{{from{{transform:scale(1.5);opacity:0}}to{{transform:scale(1);opacity:1}}}}
.hero h1{{font-family:'Outfit';font-weight:800;font-size:21px;margin:9px 0 3px;line-height:1.1;
text-shadow:0 1px 3px rgba(0,0,0,.18)}}
.hero .sub{{font-size:13px;font-weight:500;opacity:.97;text-shadow:0 1px 2px rgba(0,0,0,.16)}}
.kpis{{display:flex;gap:10px;margin:13px 0}}
.kpi{{flex:1;background:#fff;border-radius:14px;padding:11px 12px 10px;border-top:3px solid {ACCENT};
box-shadow:0 6px 18px -10px rgba(16,24,40,.28);border-left:1px solid #eceff5;border-right:1px solid #eceff5;border-bottom:1px solid #eceff5}}
.kpi.alert{{box-shadow:0 0 0 2px {DANGER}33, 0 6px 18px -10px rgba(16,24,40,.28)}}
.kpi .lab{{font-size:10px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:{MUTED};
display:flex;align-items:center;gap:6px}}
.kpi .val{{font-family:'Outfit';font-weight:800;font-size:25px;margin-top:5px;line-height:1;color:{INK}}}
.kpi .foot{{font-size:11px;font-weight:600;color:#333a48;margin-top:5px}}
.dot{{width:8px;height:8px;border-radius:50%;display:inline-block}}
.card{{background:#fff;border-radius:16px;padding:6px 6px;margin:12px 0;
box-shadow:0 8px 24px -14px rgba(16,24,40,.3);border:1px solid #eceff5}}
.card h2{{font-family:'Outfit';font-weight:700;font-size:14px;margin:10px 12px 6px;
display:flex;align-items:center;gap:8px;padding-left:8px;border-left:4px solid {ACCENT}}}
.row{{display:flex;align-items:center;gap:12px;padding:11px 12px;border-radius:12px}}
.row+.row{{border-top:1px solid #f1f3f9}}
.row .emoji{{font-size:22px;width:30px;text-align:center}}
.row .main{{flex:1;min-width:0}}
.row .name{{font-weight:600;font-size:14px}}
.row .meta{{font-size:12px;font-weight:500;color:{MUTED};margin-top:2px}}
.foot-note{{font-size:11.5px;font-weight:500;color:{MUTED};text-align:center;padding:9px 0 4px}}
.bar{{height:8px;border-radius:999px;background:#eef1f8;overflow:hidden;margin-top:6px}}
.bar>span{{display:block;height:100%;border-radius:999px}}
.badge{{font-size:11px;font-weight:700;padding:4px 10px;border-radius:999px;white-space:nowrap}}
{extra_css}
</style></head>"""


def _hero(title: str, subtitle: str, badge: str | None = None) -> str:
    badge_html = f"<div class='approved'>{html.escape(badge)}</div>" if badge else ""
    return (f"<div class='hero'>{badge_html}<span class='chip'>🎉 {BRAND}</span>"
            f"<h1>{html.escape(title)}</h1><div class='sub'>{html.escape(subtitle)}</div></div>")


def _kpi(label: str, value: str, foot: str = "", accent: str = ACCENT, alert: bool = False) -> str:
    cls = "kpi alert" if alert else "kpi"
    foot_html = f"<div class='foot'>{html.escape(foot)}</div>" if foot else ""
    return (f"<div class='{cls}' style='border-top-color:{accent}'>"
            f"<div class='lab'><span class='dot' style='background:{accent}'></span>{html.escape(label)}</div>"
            f"<div class='val'>{value}</div>{foot_html}</div>")


def _webframe(eid: str, html_content: str, height: int) -> dict:
    return {"id": eid, "component": {"WebFrameSrcdoc": {
        "htmlContent": {"literalString": html_content}, "height": height}}}


# --- inventory panel -------------------------------------------------------
def inventory_panel_html(inventory: List[Dict[str, Any]]) -> str:
    total = len(inventory)
    low = [i for i in inventory if _sev(i) != "good"]
    value = sum(max(i.get("current_stock", 0), 0) * product_meta(i["product_id"])["price"] for i in inventory)

    kpis = "".join([
        _kpi("Total SKUs", str(total), "tracked", NEUTRAL),
        _kpi("Low Stock", str(len(low)), "need attention", DANGER if low else SUCCESS, alert=bool(low)),
        _kpi("Inv. Value", f"${value/1000:.1f}k", "on hand", ACCENT),
    ])

    rows = []
    for it in sorted(inventory, key=lambda x: {"crit": 0, "warn": 1, "good": 2}[_sev(x)]):
        m = product_meta(it["product_id"])
        sev = _sev(it)
        color = _SEV_COLOR[sev]
        # bar = stock vs a healthy target, so low items read low and healthy items read full (meaningful).
        pct = max(4, min(100, round(it.get("current_stock", 0) / _target_stock(it["product_id"]) * 100)))
        rows.append(
            f"<div class='row'><div class='emoji'>{m['emoji']}</div>"
            f"<div class='main'><div class='name'>{html.escape(m['name'])}</div>"
            f"<div class='meta'>{it.get('current_stock',0)} in stock · target {_target_stock(it['product_id'])} · sold {it.get('sold',0)}</div>"
            f"<div class='bar'><span style='width:{pct}%;background:{color}'></span></div></div>"
            f"<div class='badge' style='background:{color}1f;color:{color}'>{_SEV_LABEL[sev]}</div></div>"
        )

    note = (f"{len(low)} item(s) below reorder point · refreshed live from BigQuery"
            if low else "All products above reorder point · refreshed live from BigQuery")
    return (_doc_head() + "<body><div class='wrap'>"
            + _hero("Supply Chain Dashboard", "Live inventory across your party catalog")
            + f"<div class='kpis'>{kpis}</div>"
            + "<div class='card'><h2>📦 Inventory by product</h2>" + "".join(rows)
            + f"<div class='foot-note'>{html.escape(note)}</div></div>"
            + "</div></body></html>")


# --- forecast panel (inline-SVG area chart) --------------------------------
def _nice_max(v: float) -> float:
    if v <= 0:
        return 1.0
    exp = math.floor(math.log10(v))
    base = 10 ** exp
    for m in (1, 2, 2.5, 5, 10):
        if v <= m * base:
            return m * base
    return 10 * base


def _area_chart_svg(series: List[Dict[str, Any]], reorder: int | None = None,
                    w: int = 520, h: int = 250) -> str:
    """Inline SVG area+line chart. series items: {date, sales, type in (actual|forecast)}."""
    pad_l, pad_r, pad_t, pad_b = 40, 16, 18, 30
    iw, ih = w - pad_l - pad_r, h - pad_t - pad_b
    n = len(series)
    if n == 0:
        return f"<svg width='100%' viewBox='0 0 {w} {h}'></svg>"
    raw_max = max([s["sales"] for s in series] + ([reorder] if reorder else []) + [1])
    vmax = _nice_max(raw_max)

    def x(i: int) -> float:
        return pad_l + (iw * (i / (n - 1) if n > 1 else 0.5))

    def y(v: float) -> float:
        return pad_t + ih - (ih * (v / vmax))

    pts = [(x(i), y(s["sales"])) for i, s in enumerate(series)]
    line = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    area = f"{pad_l},{pad_t+ih} " + line + f" {pad_l+iw:.1f},{pad_t+ih}"

    first_fc = next((i for i, s in enumerate(series) if s.get("type") == "forecast"), None)
    # round y grid: 5 ticks at 0..vmax
    grid = "".join(
        f"<line x1='{pad_l}' y1='{y(vmax*t):.1f}' x2='{pad_l+iw}' y2='{y(vmax*t):.1f}' "
        f"stroke='#e6eaf3' stroke-width='1'/>"
        f"<text x='{pad_l-6}' y='{y(vmax*t)+3:.1f}' text-anchor='end' font-size='10' font-weight='600' fill='{MUTED}'>{int(round(vmax*t))}</text>"
        for t in (0.0, 0.25, 0.5, 0.75, 1.0)
    )
    xlabels = "".join(
        f"<text x='{x(i):.1f}' y='{h-9}' text-anchor='middle' font-size='10' font-weight='600' fill='{MUTED}'>{html.escape(s['date'][2:])}</text>"
        for i, s in enumerate(series) if i % 2 == 0
    )
    seg_actual = " ".join(f"{px:.1f},{py:.1f}" for i, (px, py) in enumerate(pts)
                          if first_fc is None or i <= first_fc)
    seg_fc = " ".join(f"{px:.1f},{py:.1f}" for i, (px, py) in enumerate(pts)
                      if first_fc is not None and i >= first_fc)
    dots = "".join(
        f"<circle cx='{px:.1f}' cy='{py:.1f}' r='3' fill='{'#DB2777' if (first_fc is not None and i>=first_fc) else ACCENT}'/>"
        for i, (px, py) in enumerate(pts)
    )
    reorder_line = ""
    if reorder:
        ry = y(reorder)
        label = f"reorder {reorder}"
        tw = 7 * len(label) + 12
        reorder_line = (
            f"<line x1='{pad_l}' y1='{ry:.1f}' x2='{pad_l+iw}' y2='{ry:.1f}' stroke='{DANGER}' "
            f"stroke-width='1.6' stroke-dasharray='5 4'/>"
            f"<rect x='{pad_l+iw-tw:.1f}' y='{ry-16:.1f}' width='{tw}' height='14' rx='4' fill='{DANGER}' opacity='0.12'/>"
            f"<text x='{pad_l+iw-6}' y='{ry-5:.1f}' text-anchor='end' font-size='10' font-weight='800' "
            f"fill='{DANGER}'>{label}</text>"
        )
    peak_i = max(range(n), key=lambda i: series[i]["sales"])
    px_, py_ = pts[peak_i]
    peak = (f"<circle cx='{px_:.1f}' cy='{py_:.1f}' r='4.5' fill='none' stroke='{ACCENT2}' stroke-width='2'/>"
            f"<text x='{px_:.1f}' y='{py_-9:.1f}' text-anchor='middle' font-size='10' font-weight='800' "
            f"fill='{ACCENT2}'>▲ {series[peak_i]['sales']}</text>")

    return f"""<svg width='100%' viewBox='0 0 {w} {h}' preserveAspectRatio='xMidYMid meet' font-family='Inter,sans-serif'>
<defs><linearGradient id='ag' x1='0' y1='0' x2='0' y2='1'>
<stop offset='0%' stop-color='{ACCENT}' stop-opacity='0.35'/><stop offset='100%' stop-color='{ACCENT}' stop-opacity='0.02'/>
</linearGradient></defs>
{grid}
<polygon points='{area}' fill='url(#ag)'/>
<polyline points='{seg_actual}' fill='none' stroke='{ACCENT}' stroke-width='3' stroke-linejoin='round' stroke-linecap='round'/>
<polyline points='{seg_fc}' fill='none' stroke='{ACCENT2}' stroke-width='3' stroke-dasharray='6 5' stroke-linejoin='round' stroke-linecap='round'/>
{reorder_line}{dots}{peak}{xlabels}
</svg>"""


def forecast_panel_html(product_id: str, history: List[Dict[str, Any]],
                        forecast: List[Dict[str, Any]]) -> str:
    m = product_meta(product_id)
    series = (history or []) + (forecast or [])
    fc_vals = [f["sales"] for f in (forecast or [])]
    peak = max(forecast or [{"sales": 0, "date": "—"}], key=lambda r: r["sales"])
    total_fc = sum(fc_vals)
    last_year = {h["date"][-2:]: h["sales"] for h in (history or []) if h["date"].startswith("2025")}
    yoy = ""
    pk_month = peak["date"][-2:]
    if pk_month in last_year and last_year[pk_month]:
        delta = (peak["sales"] - last_year[pk_month]) / last_year[pk_month] * 100
        yoy = f"{'+' if delta>=0 else ''}{delta:.0f}%"

    reorder = 200 if product_id in ("halloween_costume", "halloween_skeleton") else 50
    kpis = "".join([
        _kpi("Peak Demand", str(peak["sales"]), f"in {peak['date']}", ACCENT),
        _kpi("6-mo Total", f"{total_fc:,}", "units forecast", ACCENT2),
        _kpi("YoY Peak", yoy or "—", "vs last year",
             SUCCESS if (yoy and not yoy.startswith('-')) else WARNING),
    ])
    legend = (f"<div style='display:flex;gap:16px;font-size:11px;font-weight:500;color:{MUTED};margin:2px 12px 6px'>"
              f"<span><span class='dot' style='background:{ACCENT}'></span> Actual</span>"
              f"<span><span class='dot' style='background:{ACCENT2}'></span> Forecast</span>"
              f"<span><span class='dot' style='background:{DANGER}'></span> Reorder point</span></div>")
    chart = _area_chart_svg(series, reorder=reorder)
    return (_doc_head() + "<body><div class='wrap'>"
            + _hero(f"{m['emoji']} {m['name']} Forecast", "Historical sales & 6-month projection (Jul–Dec 2026)")
            + f"<div class='kpis'>{kpis}</div>"
            + f"<div class='card'><h2>📈 Demand trend</h2>{legend}<div style='padding:0 8px 10px'>{chart}</div></div>"
            + "</div></body></html>")


# --- purchase-order receipt panel ------------------------------------------
def po_panel_html(po: Dict[str, Any]) -> str:
    m = product_meta(po["product_id"])
    qty = po["quantity"]
    unit = m["price"]
    subtotal = qty * unit
    ship = 49.00
    total = subtotal + ship
    receipt_css = f"""
.receipt{{padding:14px 18px 8px}}
.receipt .li{{display:flex;justify-content:space-between;font-size:13px;padding:6px 0;color:{INK}}}
.receipt .li .l{{color:{MUTED};font-weight:500}}
.receipt .li .v{{font-weight:600}}
.receipt .tot{{display:flex;justify-content:space-between;align-items:baseline;font-family:'Outfit';
font-weight:800;font-size:20px;border-top:2px dashed #dbe0ec;margin-top:8px;padding-top:12px}}
.summary{{margin:12px;padding:14px 16px;border-radius:14px;color:#fff;background:{HERO_GRADIENT};
box-shadow:0 10px 26px -14px rgba(124,58,237,.6)}}
.summary .sd{{font-size:12px;font-weight:500;opacity:.96;text-shadow:0 1px 2px rgba(0,0,0,.18)}}
.summary .big{{font-family:'Outfit';font-weight:800;font-size:22px;margin-top:2px;text-shadow:0 1px 3px rgba(0,0,0,.2)}}
"""
    return (_doc_head(receipt_css) + "<body><div class='wrap' style='position:relative'>"
            + _hero("Purchase Order Confirmed", "Your restock request has been submitted", badge="✓ APPROVED")
            + "<div class='card'><div class='receipt'>"
            + f"<div class='li'><span class='l'>PO Number</span><span class='v'>{html.escape(po['po_id'])}</span></div>"
            + f"<div class='li'><span class='l'>Product</span><span class='v'>{m['emoji']} {html.escape(m['name'])}</span></div>"
            + f"<div class='li'><span class='l'>Quantity × Unit</span><span class='v'>{qty:,} × ${unit:.2f}</span></div>"
            + f"<div class='li'><span class='l'>Subtotal</span><span class='v'>${subtotal:,.2f}</span></div>"
            + f"<div class='li'><span class='l'>Freight</span><span class='v'>${ship:,.2f}</span></div>"
            + f"<div class='tot'><span>Total</span><span>${total:,.2f}</span></div>"
            + "</div></div>"
            + "<div class='summary'>"
            + f"<div class='sd'>Order date {html.escape(po['order_date'])}</div>"
            + f"<div class='big'>🚚 Arrives {html.escape(po['estimated_delivery'])}</div>"
            + "</div>"
            + "</div></body></html>")
