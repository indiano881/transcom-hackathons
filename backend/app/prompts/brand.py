from __future__ import annotations

import re


BRAND_PROMPT = """You are Transcom's brand compliance advisor. Review the following HTML/CSS/JS files for alignment with Transcom's visual identity.

Transcom Brand Guidelines:
- Primary colors: #0C0C0C (black), #FFB800 (gold/yellow), #FFFFFF (white)
- Secondary colors: #173EDE (blue), #FFEDBE (cream), #DFF1F1 (teal)
- Font family: IBM Plex Sans (or similar clean sans-serif fonts are acceptable)
- Tone: Professional, modern, clean design
- Logo usage: Transcom logo should be used correctly if present

Your review should be encouraging and constructive, not rejecting. This is a suggestions tool, not a gate.

Rate the brand compliance:
- "pass" — Good alignment with Transcom brand (uses brand colors, clean fonts, professional look)
- "warn" — Partial alignment (some off-brand colors or fonts, but generally acceptable)
- "fail" — Significant brand deviation (but still just a recommendation, not a block)

Note: "fail" for brand does NOT block deployment — it's just feedback.

Respond with ONLY valid JSON in this exact format:
{
  "status": "pass" | "warn" | "fail",
  "summary": "One encouraging sentence about brand alignment",
  "details": ["Suggestion 1", "Suggestion 2"]
}

FILES TO ANALYZE:
"""

PARTNER_BRAND_PROMPT = """You are a brand compliance advisor. A user has uploaded static HTML/CSS/JS files intended for a partner company. Your job is to extract the partner's brand identity from their webpage HTML, then check the uploaded files against it.

PARTNER WEBPAGE ({partner_url}):
--- partner page HTML ---
{partner_html}
--- end partner page HTML ---

From the partner webpage above, identify:
- Primary and secondary brand colors (hex values)
- Font families used
- Visual tone and style (modern, playful, corporate, etc.)

Then review the uploaded files below for alignment with that partner brand.

Rate the brand compliance:
- "pass" — Good alignment with the partner's brand identity
- "warn" — Partial alignment (some off-brand colors or fonts, but generally acceptable)
- "fail" — Significant brand deviation (but still just a recommendation, not a block)

Note: "fail" for brand does NOT block deployment — it's just feedback.

Respond with ONLY valid JSON in this exact format:
{{
  "status": "pass" | "warn" | "fail",
  "summary": "One encouraging sentence about brand alignment with {partner_url}",
  "details": ["Suggestion 1", "Suggestion 2"]
}}

FILES TO ANALYZE:
"""


def _strip_html_noise(html: str) -> str:
    """Remove script, style, svg, and noscript blocks to reduce token count."""
    html = re.sub(r'<script[\s\S]*?</script>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<style[\s\S]*?</style>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<svg[\s\S]*?</svg>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<noscript[\s\S]*?</noscript>', '', html, flags=re.IGNORECASE)
    # Collapse whitespace
    html = re.sub(r'\s{2,}', ' ', html)
    return html.strip()


def build_brand_prompt(partner_url: str | None = None, partner_html: str | None = None) -> str:
    if partner_url and partner_html:
        cleaned = _strip_html_noise(partner_html)
        # Truncate to ~15KB to stay within token budget
        truncated = cleaned[:15000]
        return PARTNER_BRAND_PROMPT.format(
            partner_url=partner_url,
            partner_html=truncated,
        )
    return BRAND_PROMPT
