"""Frontend application tests: static asset delivery, HTML structure, accessibility, and navigation."""

import os
import pytest
import re


@pytest.mark.asyncio
async def test_frontend_html_serving(async_client):
    """Verify that root request with text/html returns index.html correctly."""
    response = await async_client.get("/", headers={"Accept": "text/html,application/xhtml+xml"})
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    content = response.text
    assert "<title>IRecruit — AI Resume Intelligence & Job Alignment Engine</title>" in content
    assert "Analysis Workbench" in content
    assert "Candidate Intelligence Dashboard" in content
    assert "support@irecruit-intelligence.io" in content
    assert "+1 (800) 555-0199" in content
    assert "2026 IRecruit Intelligence Systems" in content


@pytest.mark.asyncio
async def test_frontend_static_assets(async_client):
    """Verify CSS, JS, and SVG static files are served with proper content types."""
    # Test CSS
    css_res = await async_client.get("/styles.css")
    assert css_res.status_code == 200
    assert "text/css" in css_res.headers.get("content-type", "")
    assert "--font-family" in css_res.text

    # Test JS
    js_res = await async_client.get("/app.js")
    assert js_res.status_code == 200
    assert "javascript" in js_res.headers.get("content-type", "")
    assert "IRecruit AI Resume Intelligence" in js_res.text

    # Test Favicon SVG
    svg_res = await async_client.get("/favicon.svg")
    assert svg_res.status_code == 200
    assert "image/svg+xml" in svg_res.headers.get("content-type", "")

    # Test 404 Page
    nf_res = await async_client.get("/404.html")
    assert nf_res.status_code == 200
    assert "Page Not Found" in nf_res.text


def test_html_internal_anchor_integrity():
    """Verify all hash links in index.html match defined IDs in the document."""
    html_path = os.path.join("frontend", "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Find all href="#..." anchors
    anchors = re.findall(r'href="#([a-zA-Z0-9_\-]+)"', html)
    # Find all id="..." declarations
    element_ids = set(re.findall(r'id="([a-zA-Z0-9_\-]+)"', html))

    for anchor in anchors:
        assert anchor in element_ids, f"Anchor #{anchor} does not correspond to an element ID in index.html"


def test_no_placeholders_and_valid_compliance_text():
    """Ensure no Lorem ipsum, placeholder dummy strings, or broken links exist."""
    html_path = os.path.join("frontend", "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    assert "lorem ipsum" not in html.lower()
    assert "todo" not in html.lower()
    assert "2026" in html
    assert "mailto:support@irecruit-intelligence.io" in html
    assert "tel:+18005550199" in html
