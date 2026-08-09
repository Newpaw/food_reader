from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "calorie-tracker" / "frontend"

PAGES = {
    "index.html": "add",
    "history.html": "history",
    "metrics.html": "metrics",
    "health.html": "health",
    "assistant.html": "assistant",
    "profile.html": "profile",
}

EXPECTED_NAV_ITEMS = [
    ("add", "index.html"),
    ("history", "history.html"),
    ("metrics", "metrics.html"),
    ("health", "health.html"),
    ("assistant", "assistant.html"),
    ("profile", "profile.html"),
]


def main() -> None:
    navigation_source = (FRONTEND / "navigation.js").read_text(encoding="utf-8")

    for nav_id, href in EXPECTED_NAV_ITEMS:
        assert f"id: '{nav_id}'" in navigation_source, f"missing nav id: {nav_id}"
        assert f"href: '{href}'" in navigation_source, f"missing nav href: {href}"

    assert "window.localStorage.getItem('food-reader:locale')" in navigation_source
    assert "window.navigator?.language" in navigation_source
    assert "cs: 'Zdraví'" in navigation_source
    assert "cs: 'AI asistent'" in navigation_source
    assert "repeat(6, minmax(0, 1fr))" in navigation_source
    assert "food-reader:localechange" in navigation_source
    assert "mobile-ux.js?v=20260809-3" in navigation_source
    assert "mobile-polish.css" in navigation_source
    assert "responsive-fix.css" in navigation_source
    assert "document.body.appendChild(nav)" in navigation_source

    mobile_polish = FRONTEND / "mobile-polish.css"
    mobile_ux = FRONTEND / "mobile-ux.js"
    responsive_fix = FRONTEND / "responsive-fix.css"
    assert mobile_polish.exists(), "shared mobile polish stylesheet is missing"
    assert mobile_ux.exists(), "shared mobile UX script is missing"
    assert responsive_fix.exists(), "narrow-screen responsive fix stylesheet is missing"

    mobile_ux_source = mobile_ux.read_text(encoding="utf-8")
    responsive_fix_source = responsive_fix.read_text(encoding="utf-8")
    assert "(max-width: 979px)" in mobile_ux_source
    assert "@media (max-width: 979px)" in responsive_fix_source
    assert "grid-template-columns: repeat(6, minmax(0, 1fr))" in responsive_fix_source
    assert 'body[data-page="health"] .health-charts-grid' in responsive_fix_source
    assert 'body[data-page="assistant"] .assistant-shell' in responsive_fix_source

    script_tag = '<script type="module" src="navigation.js?v=20260809-1"></script>'
    for filename, page_id in PAGES.items():
        source = (FRONTEND / filename).read_text(encoding="utf-8")
        assert source.count(script_tag) == 1, f"{filename} must load shared navigation exactly once"
        assert f'data-page="{page_id}"' in source, f"{filename} has wrong or missing data-page"
        assert 'class="desktop-nav"' in source, f"{filename} is missing desktop navigation"
        assert 'class="bottom-nav"' in source, f"{filename} is missing mobile navigation"

    assistant_source = (FRONTEND / "assistant.html").read_text(encoding="utf-8")
    assert '<title>Food Reader | AI Assistant</title>' in assistant_source
    assert '<body data-page="assistant">' in assistant_source

    print("navigation regression tests: OK")


if __name__ == "__main__":
    main()
