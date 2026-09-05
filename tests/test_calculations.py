"""
Focused tests for clinical calculation functions in vaccine_coverage.py.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import math
import pytest
import tempfile
import csv

from vaccine_coverage import (
    calculate_score,
    calculate_meld_na,
    calculate_qtc,
    calculate_bmi_z,
    convert_hba1c,
    calculate_apri_fib4,
    assess_row,
    process_csv,
    _safe_float,
    _safe_int,
)


class TestSafeConversions:
    """Test input conversion helpers."""

    def test_safe_float_with_number(self):
        assert _safe_float(42) == 42.0
        assert _safe_float(3.14) == 3.14

    def test_safe_float_with_string(self):
        assert _safe_float("3.14") == 3.14
        assert _safe_float("100") == 100.0

    def test_safe_float_with_none(self):
        assert _safe_float(None) == 0.0

    def test_safe_float_with_invalid(self):
        assert _safe_float("not_a_number") == 0.0

    def test_safe_float_with_default(self):
        assert _safe_float(None, 5.0) == 5.0
        assert _safe_float("bad", 10.0) == 10.0

    def test_safe_int_basic(self):
        assert _safe_int(42) == 42
        assert _safe_int("100") == 100
        assert _safe_int(None) == 0


class TestCalculateScore:
    """Test generic score calculation."""

    def test_basic_score(self):
        result = calculate_score(value=10)
        assert isinstance(result, dict)
        assert "score" in result
        assert "inputs" in result
        assert result["inputs"] == 1

    def test_multiple_inputs(self):
        result = calculate_score(a=10, b=20, c=30)
        assert result["inputs"] == 3

    def test_empty_inputs_defaults(self):
        result = calculate_score()
        assert result["inputs"] == 1
        assert "score" in result


class TestMELDNa:
    """Test MELD-Na score calculation."""

    def test_basic_meld(self):
        result = calculate_meld_na(bilirubin=2.0, creatinine=1.2, inr=1.5, sodium=135)
        assert result["score_type"] == "MELD-Na"
        assert 6 <= result["score"] <= 40

    def test_dialysis_adjustment(self):
        result = calculate_meld_na(bilirubin=3.0, creatinine=0.8, inr=2.0, sodium=130, dialysis=True)
        assert result["score_type"] == "MELD-Na"
        assert result["creatinine"] == 4.0  # capped at 4 for dialysis

    def test_low_values_clamped(self):
        result = calculate_meld_na(bilirubin=0.1, creatinine=0.1, inr=0.5, sodium=140)
        assert result["score"] >= 6  # minimum MELD

    def test_meld_with_string_inputs(self):
        result = calculate_meld_na(bilirubin="2.5", creatinine="1.5", inr="1.8", sodium="132")
        assert result["score_type"] == "MELD-Na"
        assert result["bilirubin"] == 2.5

    def test_meld_none_values_default(self):
        result = calculate_meld_na(bilirubin=None, creatinine=None, inr=None, sodium=None)
        assert "score" in result


class TestQTc:
    """Test QTc calculation."""

    def test_basic_qtc_with_rr(self):
        result = calculate_qtc(qt_ms=400, rr_ms=800)
        assert result["score_type"] == "QTc_Bazett"
        assert result["qt_ms"] == 400.0

    def test_qtc_from_heart_rate(self):
        result = calculate_qtc(qt_ms=420, hr_bpm=60)
        assert result["score_type"] == "QTc_Bazett"
        assert result["rr_ms"] == 1000.0  # 60000/60

    def test_qtc_critical_prolonged(self):
        result = calculate_qtc(qt_ms=520, rr_ms=800)
        assert "CRITICAL" in result["interpretation"]

    def test_qtc_normal(self):
        result = calculate_qtc(qt_ms=380, rr_ms=900)
        assert result["interpretation"] == "Normal QTc"

    def test_qtc_with_defaults(self):
        result = calculate_qtc(qt_ms=None)
        assert result["score_type"] == "QTc_Bazett"
        assert "interpretation" in result


class TestBMI:
    """Test BMI calculation."""

    def test_normal_bmi(self):
        result = calculate_bmi_z(weight_kg=70, height_cm=175)
        assert result["score_type"] == "BMI"
        assert 22 <= result["bmi"] <= 23

    def test_bmi_underweight(self):
        result = calculate_bmi_z(weight_kg=45, height_cm=170)
        assert result["category"] == "Underweight"

    def test_bmi_overweight(self):
        result = calculate_bmi_z(weight_kg=85, height_cm=175)
        assert result["category"] == "Overweight"

    def test_bmi_obese(self):
        result = calculate_bmi_z(weight_kg=120, height_cm=175)
        assert result["category"] == "Obese"

    def test_bmi_invalid_input(self):
        result = calculate_bmi_z(weight_kg=0, height_cm=0)
        assert "error" in result

    def test_bmi_with_string_age(self):
        result = calculate_bmi_z(weight_kg=70, height_cm=175, age_months="48")
        assert result["score_type"] == "BMI"


class TestHbA1c:
    """Test HbA1c conversion."""

    def test_hba1c_to_eag(self):
        result = convert_hba1c(hba1c_percent=7.0)
        assert result["score_type"] == "HbA1c_to_eAG"
        assert result["hba1c_percent"] == 7.0
        # eAG = 28.7 * 7.0 - 46.7 = 154.2
        assert abs(result["eag_mgdl"] - 154.2) < 1.0

    def test_eag_to_hba1c(self):
        result = convert_hba1c(eag_mgdl=154.2)
        assert result["score_type"] == "eAG_to_HbA1c"
        assert abs(result["hba1c_percent"] - 7.0) < 0.5

    def test_hba1c_none_defaults(self):
        result = convert_hba1c()
        assert "error" in result


class TestAPRI:
    """Test APRI/FIB-4 calculation."""

    def test_basic_apri(self):
        result = calculate_apri_fib4(ast_u_l=45, platelets_109=250)
        assert result["score_type"] == "APRI"
        assert "score" in result
        assert "interpretation" in result

    def test_apri_with_fib4(self):
        result = calculate_apri_fib4(ast_u_l=60, alt_u_l=45, platelets_109=200, age_years=55)
        assert result["score_type"] == "APRI"
        assert "fib4" in result

    def test_apri_high_fibrosis(self):
        result = calculate_apri_fib4(ast_u_l=120, platelets_109=100)
        assert "Significant fibrosis" in result["interpretation"]

    def test_apri_low_platelets_default(self):
        result = calculate_apri_fib4(ast_u_l=30, platelets_109=0)
        assert result["score_type"] == "APRI"


class TestAssessRow:
    """Test row routing logic."""

    def test_meld_route(self):
        row = {"bilirubin": 2.5, "creatinine": 1.2, "inr": 1.5, "sodium": 135}
        result = assess_row(row)
        assert result["score_type"] == "MELD-Na"

    def test_qtc_route(self):
        row = {"qt": 420, "rr_ms": 850}
        result = assess_row(row)
        assert result["score_type"] == "QTc_Bazett"

    def test_bmi_route(self):
        row = {"weight_kg": 70, "height_cm": 175}
        result = assess_row(row)
        assert result["score_type"] == "BMI"

    def test_hba1c_route(self):
        row = {"hba1c_percent": 6.5}
        result = assess_row(row)
        assert result["score_type"] == "HbA1c_to_eAG"

    def test_apri_route(self):
        row = {"ast_u_l": 45, "platelets_109": 250}
        result = assess_row(row)
        assert result["score_type"] == "APRI"

    def test_generic_score_fallback(self):
        row = {"value": 10}
        result = assess_row(row)
        assert "score" in result


class TestProcessCSV:
    """Test CSV processing with validation."""

    def test_basic_csv_processing(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            f.write("id,value,qty\n")
            f.write("A,10,2\n")
            f.write("B,20,3\n")
            inp = f.name

        out = inp.replace('.csv', '_out.csv')
        try:
            results = process_csv(inp, out)
            assert len(results) == 2
            assert os.path.exists(out)

            # Verify output CSV
            with open(out, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                assert len(rows) == 2
        finally:
            os.unlink(inp)
            if os.path.exists(out):
                os.unlink(out)

    def test_path_traversal_prevention(self):
        with pytest.raises((ValueError, FileNotFoundError)):
            process_csv("../../../etc/passwd", "output.csv")

    def test_same_input_output_rejected(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("id,value\nA,1\n")
            inp = f.name
        try:
            with pytest.raises(ValueError):
                process_csv(inp, inp)
        finally:
            os.unlink(inp)
