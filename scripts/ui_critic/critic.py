"""Vision critic that assesses the demo impact of an A2UI screen rendered in the GE side-canvas.

Mirrors the rag_pg_ip image-critic structure (structured output, temperature 0, graceful fallback) but
scores actual pixels: it takes a PNG screenshot and returns per-dimension scores + concrete fixes.
"""
import os
from typing import List

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

PROJECT = os.environ.get("PROJECT_ID", "wortz-project-352116")
LOCATION = os.environ.get("CRITIC_LOCATION", "us-central1")
CRITIC_MODEL = os.environ.get("CRITIC_MODEL", "gemini-2.5-flash")

_client = genai.Client(vertexai=True, project=PROJECT, location=LOCATION)


class UICritique(BaseModel):
    visual_hierarchy: int = Field(description="1-5: is the eye guided; clear title > KPIs > detail?")
    brand_cohesion: int = Field(description="1-5: cohesive festive-premium party-store brand (gradient hero, consistent color/spacing)?")
    color_contrast: int = Field(description="1-5: legible contrast; status colors (green/amber/red) meaningful and accessible?")
    info_density: int = Field(description="1-5: right amount of info, not sparse or cramped, good use of the ~520px canvas?")
    delight_wow: int = Field(description="1-5: does it impress in a live demo (polish, micro-touches, imagery)?")
    chart_quality: int = Field(description="1-5: quality of any data-viz/receipt/data presentation (clarity, labeling, styling)?")
    readability: int = Field(description="1-5: type sizes/weights readable; no truncation/overflow?")
    cta_clarity: int = Field(description="1-5: is the next action obvious and inviting?")
    overall: float = Field(description="0-5 overall demo-impact score (may be decimal).")
    strengths: List[str] = Field(default_factory=list, description="What already works well.")
    top_fixes: List[str] = Field(default_factory=list, description="3-6 concrete, prioritized, specific CSS/layout changes to raise demo impact.")
    verdict: str = Field(default="", description="One-line verdict on demo readiness.")


_RUBRIC = (
    "You are a principal product designer reviewing a screen that will be shown LIVE in a sales demo, "
    "rendered inside Google Gemini Enterprise's narrow side-canvas (~520px wide). The product is a "
    "playful-but-premium PARTY STORE supply-chain assistant. Judge it as a demo asset: it must look "
    "polished, on-brand (festive gradient hero, crisp KPI tiles, meaningful status colors), and instantly "
    "readable. Be a demanding critic — reserve 5s for genuinely excellent, and make every fix concrete "
    "and actionable (name the element and the exact change: color, size, spacing, layout, missing element). "
    "Score each dimension 1-5, give an overall 0-5, list strengths, and list the highest-leverage fixes."
)


def assess(png_path: str, screen_name: str, cta_labels: List[str] | None = None) -> UICritique:
    with open(png_path, "rb") as f:
        img = f.read()
    cta_note = ""
    if cta_labels:
        cta_note = (
            "\n\nNOTE: interactive action buttons render directly BELOW this panel in GE and are NOT in "
            f"the screenshot: {cta_labels}. Judge cta_clarity on whether the panel + these buttons make "
            "the next step obvious; do NOT penalize for 'missing buttons' that are in this list."
        )
    prompt = f"{_RUBRIC}\n\nSCREEN UNDER REVIEW: {screen_name}\nAssess the attached screenshot.{cta_note}"
    try:
        resp = _client.models.generate_content(
            model=CRITIC_MODEL,
            contents=[types.Part.from_bytes(data=img, mime_type="image/png"), prompt],
            config=types.GenerateContentConfig(
                temperature=0.0,
                response_mime_type="application/json",
                response_schema=UICritique,
            ),
        )
        return resp.parsed
    except Exception as e:  # noqa: BLE001
        print(f"--- critic error for {screen_name}: {e} ---")
        return UICritique(
            visual_hierarchy=0, brand_cohesion=0, color_contrast=0, info_density=0,
            delight_wow=0, chart_quality=0, readability=0, cta_clarity=0, overall=0.0,
            strengths=[], top_fixes=[f"critic failed: {e}"], verdict="ERROR",
        )
