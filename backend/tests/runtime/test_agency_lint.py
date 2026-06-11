"""Agency surface static lint."""

from app.core.runtime.projection.agency_lint import lint_agency_surface_source


def test_morning_brief_passes_agency_lint():
    issues = lint_agency_surface_source("app.product.morning_brief")
    fails = [i for i in issues if i.startswith("FAIL:")]
    assert fails == [], fails
