"""Tests for mobile responsiveness, cross-screen breakpoints, and touch UX."""

import os
import re
import pytest


def test_responsive_breakpoints_present():
    """Verify that all target device breakpoints (320, 390/375, 430, 768, 1024, 1280) exist in styles.css."""
    css_path = os.path.join("frontend", "styles.css")
    with open(css_path, "r", encoding="utf-8") as f:
        css = f.read()

    breakpoints = [
        "320px",
        "390px",
        "430px",
        "768px",
        "1024px",
        "1280px",
    ]
    for bp in breakpoints:
        assert bp in css, f"Breakpoint {bp} is missing from styles.css"


def test_touch_target_accessibility():
    """Verify that touch target rules enforce minimum 44px height for touch interactions."""
    css_path = os.path.join("frontend", "styles.css")
    with open(css_path, "r", encoding="utf-8") as f:
        css = f.read()

    assert "min-height: 44px" in css
    assert "min-width: 44px" in css
    # Ensure iOS auto-zoom prevention rule is set (font-size: 16px on inputs)
    assert "font-size: 16px" in css


def test_no_unintended_horizontal_overflow():
    """Verify that CSS contains horizontal overflow prevention rules."""
    css_path = os.path.join("frontend", "styles.css")
    with open(css_path, "r", encoding="utf-8") as f:
        css = f.read()

    assert "overflow-x: hidden" in css


def test_prefers_reduced_motion_support():
    """Verify accessible support for users with motion sensitivity."""
    css_path = os.path.join("frontend", "styles.css")
    with open(css_path, "r", encoding="utf-8") as f:
        css = f.read()

    assert "prefers-reduced-motion: reduce" in css


def test_mobile_menu_accessibility():
    """Verify mobile menu button has ARIA attributes and labels in index.html."""
    html_path = os.path.join("frontend", "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    assert 'aria-label="Toggle mobile menu"' in html
    assert 'aria-expanded="false"' in html
    assert 'id="mobileMenuBtn"' in html
