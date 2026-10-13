"""Regression tests for the vaccine-specific estimator."""
import math
import pytest
from coverage import estimate_coverage
from vaccine_coverage import assess_row


def test_reference_wilson_interval():
    result = estimate_coverage(100, 80, 90, 72)
    assert result["coverage_percent"] == 80.0
    assert result["dropout_percent"] == 20.0
    assert result["ci_lower_percent"] == pytest.approx(71.14, abs=0.02)
    assert result["ci_upper_percent"] == pytest.approx(86.67, abs=0.02)


def test_zero_vaccination_and_full_coverage():
    assert estimate_coverage(100, 0)["ci_lower_percent"] == 0
    assert estimate_coverage(100, 100)["ci_upper_percent"] == 100


def test_zero_dose_series_has_undefined_dropout():
    assert estimate_coverage(100, 0, 0, 0)["dropout_percent"] is None


@pytest.mark.parametrize("kwargs", [
    {"population": 0, "vaccinated": 0},
    {"population": 100, "vaccinated": 101},
    {"population": 100, "vaccinated": -1},
    {"population": True, "vaccinated": 0},
    {"population": 20.5, "vaccinated": 1},
    {"population": 100, "vaccinated": 80, "first_dose": 50},
    {"population": 100, "vaccinated": 80, "first_dose": 50, "final_dose": 51},
    {"population": 100, "vaccinated": 80, "confidence": float("nan")},
    {"population": 100, "vaccinated": 80, "confidence": 1},
])
def test_invalid_counts(kwargs):
    with pytest.raises(ValueError):
        estimate_coverage(**kwargs)


def test_legacy_csv_row_routing_supports_coverage():
    result = assess_row({"population": "100", "vaccinated": "80", "first_dose": "90", "final_dose": "72"})
    assert result["coverage_percent"] == 80.0
    assert result["dropout_percent"] == 20.0


def test_invalid_row_reports_error():
    result = assess_row({"population": "0", "vaccinated": "1"})
    assert "error" in result


def test_optional_api():
    from fastapi.testclient import TestClient
    from agents.api import app
    client = TestClient(app)
    assert client.post("/api/coverage", json={"population": 100, "vaccinated": 80}).json()["coverage_percent"] == 80
    assert client.post("/api/coverage", json={"population": 100, "vaccinated": 101}).status_code == 422
