"""Render an A2UI WebFrameSrcdoc panel to a PNG via headless Chromium.

GE renders the WebFrameSrcdoc htmlContent in a sandboxed iframe; loading that same self-contained HTML
in headless Chromium and screenshotting it is a faithful preview of the GE side-canvas — no GE auth
needed. Run the flywheel with: `uv run --with playwright python scratch/ui_critic/flywheel.py`.
"""
import os
import tempfile

from playwright.sync_api import sync_playwright


def extract_panel_html(payload: list) -> str | None:
    """Pull the WebFrameSrcdoc inline HTML out of an A2UI command list."""
    for cmd in payload:
        su = cmd.get("surfaceUpdate") if isinstance(cmd, dict) else None
        if not su:
            continue
        for comp in su.get("components", []):
            c = comp.get("component", {})
            if "WebFrameSrcdoc" in c:
                return c["WebFrameSrcdoc"]["htmlContent"]["literalString"]
    return None


def render_html_to_png(html: str, out_path: str, width: int = 560) -> str:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html)
        tmp = f.name
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = browser.new_page(viewport={"width": width, "height": 900}, device_scale_factor=2)
            try:
                page.goto(f"file://{tmp}", wait_until="networkidle", timeout=30000)
            except Exception:
                # networkidle can hang if a font CDN is slow; fall back to load + delay.
                page.goto(f"file://{tmp}", wait_until="load", timeout=30000)
            page.wait_for_timeout(700)  # let fonts/SVG settle
            page.screenshot(path=out_path, full_page=True)
            browser.close()
    finally:
        os.unlink(tmp)
    return out_path


def render_payload_to_png(payload: list, out_path: str, width: int = 560) -> str:
    html = extract_panel_html(payload)
    if not html:
        raise ValueError("no WebFrameSrcdoc panel found in payload")
    return render_html_to_png(html, out_path, width=width)
