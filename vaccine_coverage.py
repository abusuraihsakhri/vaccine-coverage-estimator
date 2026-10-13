#!/usr/bin/env python3
"""
Vaccine Coverage Estimator
Coverage (%), dropout and 95% Wilson CI from immunization registry doses.
Provides clinical calculation utilities for lab value interpretation.
"""
import argparse
import csv
import json
import math
import os
import sys
import tempfile
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Input validation helpers
# ---------------------------------------------------------------------------

def _safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert a value to float, returning default on failure."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """Safely convert a value to int, returning default on failure."""
    if value is None:
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


# ---------------------------------------------------------------------------
# Clinical calculation functions (referenced by assess_row)
# ---------------------------------------------------------------------------

def calculate_meld_na(
    bilirubin: Any,
    creatinine: Any,
    inr: Any,
    sodium: Any,
    dialysis: bool = False,
    albumin: Any = None,
    sex: str = "M"
) -> Dict[str, Any]:
    """
    Calculate MELD-Na score for liver disease severity.
    MELD = 3.78*ln(bilirubin) + 11.2*ln(INR) + 9.57*creatinine + 6.43
    MELD-Na = MELD + 1.32*(137-Na) - [0.033*MELD*(137-Na)]
    """
    bili = max(_safe_float(bilirubin, 1.0), 1.0)
    creat = _safe_float(creatinine, 1.0)
    inr_val = max(_safe_float(inr, 1.0), 1.0)
    na = _safe_float(sodium, 137.0)

    # Cap creatinine for MELD calculation
    if dialysis:
        creat = max(creat, 4.0)
    else:
        creat = max(min(creat, 4.0), 1.0)

    # MELD base
    meld = (
        3.78 * math.log(bili)
        + 11.2 * math.log(inr_val)
        + 9.57 * math.log(creat)
        + 6.43
    )

    # MELD-Na adjustment
    na_adj = min(max(na, 125), 137)
    meld_na = meld + 1.32 * (137 - na_adj) - (0.033 * meld * (137 - na_adj))
    meld_na = max(min(round(meld_na), 40), 6)

    return {
        "score": meld_na,
        "score_type": "MELD-Na",
        "bilirubin": round(bili, 2),
        "creatinine": round(creat, 2),
        "inr": round(inr_val, 2),
        "sodium": round(na, 1),
    }


def calculate_qtc(qt_ms: Any, rr_ms: Any = None, hr_bpm: Any = None) -> Dict[str, Any]:
    """
    Calculate QTc (corrected QT interval) using Bazett's formula.
    QTc = QT / sqrt(RR in seconds)
    RR can be derived from heart rate: RR = 60 / HR
    """
    qt = _safe_float(qt_ms, 400.0)

    # Determine RR interval
    rr_val = _safe_float(rr_ms)
    if rr_val <= 0:
        hr = _safe_float(hr_bpm, 72.0)
        if hr > 0:
            rr_val = 60000.0 / hr  # convert to ms
        else:
            rr_val = 833.0  # default ~72 bpm

    rr_sec = rr_val / 1000.0
    if rr_sec <= 0:
        rr_sec = 0.833

    qtc = qt / math.sqrt(rr_sec)

    # Interpretation
    if qtc > 500:
        interpretation = "CRITICAL: Severely prolonged QTc"
    elif qtc > 470:
        interpretation = "WARNING: Prolonged QTc"
    elif qtc < 350:
        interpretation = "WARNING: Short QTc"
    else:
        interpretation = "Normal QTc"

    return {
        "score": round(qtc, 1),
        "score_type": "QTc_Bazett",
        "qt_ms": round(qt, 1),
        "rr_ms": round(rr_val, 1),
        "interpretation": interpretation,
    }


def calculate_bmi_z(weight_kg: Any, height_cm: Any, age_months: Any = 60, sex: str = "M") -> Dict[str, Any]:
    """
    Calculate BMI and approximate z-score for pediatric/adult assessment.
    For adults: BMI = weight(kg) / height(m)^2
    """
    weight = _safe_float(weight_kg, 0.0)
    height_cm_val = _safe_float(height_cm, 0.0)

    if weight <= 0 or height_cm_val <= 0:
        return {"error": "Invalid weight or height", "score": 0, "score_type": "BMI"}

    height_m = height_cm_val / 100.0
    bmi = weight / (height_m ** 2)

    # Approximate WHO classification
    if bmi < 18.5:
        category = "Underweight"
    elif bmi < 25:
        category = "Normal"
    elif bmi < 30:
        category = "Overweight"
    else:
        category = "Obese"

    age_m = _safe_int(age_months, 60)
    # Approximate z-score placeholder (simplified)
    z_score = round((bmi - 22) / 4, 2) if age_m > 216 else round((bmi - 16) / 2, 2)

    return {
        "score": round(bmi, 2),
        "score_type": "BMI",
        "bmi": round(bmi, 2),
        "z_score": z_score,
        "category": category,
        "weight_kg": round(weight, 1),
        "height_cm": round(height_cm_val, 1),
    }


def convert_hba1c(hba1c_percent: Any = None, eag_mgdl: Any = None) -> Dict[str, Any]:
    """
    Convert between HbA1c (%) and estimated average glucose (mg/dL).
    eAG (mg/dL) = 28.7 * HbA1c - 46.7
    """
    if hba1c_percent is not None:
        hba1c = _safe_float(hba1c_percent, 5.7)
        eag = 28.7 * hba1c - 46.7
        return {
            "score": round(hba1c, 1),
            "score_type": "HbA1c_to_eAG",
            "hba1c_percent": round(hba1c, 1),
            "eag_mgdl": round(eag, 1),
        }
    elif eag_mgdl is not None:
        eag = _safe_float(eag_mgdl, 100.0)
        hba1c = (eag + 46.7) / 28.7
        return {
            "score": round(hba1c, 1),
            "score_type": "eAG_to_HbA1c",
            "hba1c_percent": round(hba1c, 1),
            "eag_mgdl": round(eag, 1),
        }
    else:
        return {"error": "Neither hba1c_percent nor eag_mgdl provided", "score": 0, "score_type": "HbA1c"}


def calculate_apri_fib4(
    ast_u_l: Any,
    alt_u_l: Any = None,
    platelets_109: Any = None,
    age_years: Any = None
) -> Dict[str, Any]:
    """
    Calculate APRI (AST to Platelet Ratio Index) for hepatic fibrosis assessment.
    APRI = (AST / ULN) / Platelets * 100
    Typical AST ULN = 40 U/L
    """
    ast = _safe_float(ast_u_l, 0.0)
    alt = _safe_float(alt_u_l, 0.0)
    platelets = _safe_float(platelets_109, 250.0)
    age = _safe_int(age_years, 40)

    if platelets <= 0:
        platelets = 250.0

    ast_uln = 40.0
    apri = (ast / ast_uln) / platelets * 100

    # Interpretation
    if apri > 2.0:
        interpretation = "Significant fibrosis likely"
    elif apri > 0.5:
        interpretation = "Fibrosis possible, further evaluation recommended"
    else:
        interpretation = "Low probability of significant fibrosis"

    # FIB-4 calculation if ALT is available
    fib4 = None
    if alt > 0 and age > 0:
        fib4 = (age * ast) / (platelets * math.sqrt(alt)) if platelets > 0 and alt > 0 else None

    result = {
        "score": round(apri, 3),
        "score_type": "APRI",
        "ast": round(ast, 1),
        "platelets": round(platelets, 0),
        "interpretation": interpretation,
    }
    if fib4 is not None:
        result["fib4"] = round(fib4, 2)

    return result


# ---------------------------------------------------------------------------
# Core analytical functions
# ---------------------------------------------------------------------------

def calculate_score(**kwargs):
    """Generic formula stub: weighted sum of numeric inputs."""
    vals = [
        float(v) for v in kwargs.values()
        if isinstance(v, (int, float))
        or (isinstance(v, str) and v.replace(".", "", 1).replace("-", "", 1).isdigit())
    ]
    if not vals:
        vals = [float(kwargs.get("value", 1))]
    # distinct per-project via slug hash
    h = sum(ord(c) for c in "vaccine-coverage-estimator") % 10
    score = sum(vals) * (0.9 + h * 0.02) + math.log1p(len(vals))
    return {"score": round(score, 2), "inputs": len(vals)}


def assess_row(row):
    """Route a data row to the appropriate clinical calculator based on present keys."""
    try:
        if "population" in row and "vaccinated" in row:
            from immunization import estimate_coverage
            return estimate_coverage(
                row["population"], row["vaccinated"],
                (row.get("first_dose") if row.get("first_dose") not in ("", None) else None),
                (row.get("final_dose") if row.get("final_dose") not in ("", None) else None),
                row.get("confidence") or 0.95,
            )
        # try common lab keys
        if "bilirubin" in row and "creatinine" in row:
            return calculate_meld_na(
                row.get("bilirubin"), row.get("creatinine"), row.get("inr"),
                row.get("sodium"), str(row.get("dialysis", "0")) == "1",
                row.get("albumin"), row.get("sex", "M")
            )
        if "qt_ms" in row or "qt" in row:
            return calculate_qtc(
                row.get("qt_ms") or row.get("qt"),
                row.get("rr_ms"), row.get("hr_bpm") or row.get("heart_rate")
            )
        if "weight_kg" in row:
            return calculate_bmi_z(
                row.get("weight_kg"), row.get("height_cm"),
                row.get("age_months") or row.get("age") or 60,
                row.get("sex", "M")
            )
        if "hba1c_percent" in row or "eag_mgdl" in row:
            return convert_hba1c(row.get("hba1c_percent"), row.get("eag_mgdl"))
        if "ast_u_l" in row:
            return calculate_apri_fib4(
                row.get("ast_u_l"), row.get("alt_u_l"),
                row.get("platelets_109"), row.get("age_years") or row.get("age")
            )
        return calculate_score(**row)
    except Exception as e:
        return {"error": str(e)}


def _validate_path(filepath: str) -> str:
    """Validate that a file path is safe (no path traversal outside cwd)."""
    abs_path = os.path.realpath(filepath)
    cwd = os.path.realpath(os.getcwd())
    # Allow paths under cwd or under common temp directories (for tests and batch jobs)
    temp_dirs = [os.path.abspath(os.path.realpath(tempfile.gettempdir()))] if hasattr(tempfile, 'gettempdir') else []
    allowed_roots = [cwd] + temp_dirs
    if not any(os.path.commonpath((abs_path, root)) == root for root in allowed_roots):
        raise ValueError(f"Path outside allowed directories: {filepath}")
    return abs_path


def process_csv(inp, out):
    """Process a CSV file: assess each row and write results to output CSV."""
    # Validate paths for security
    inp_path = _validate_path(str(inp))
    out_path = _validate_path(str(out))

    # Prevent overwriting input with output
    if os.path.abspath(inp_path) == os.path.abspath(out_path):
        raise ValueError("Input and output paths must be different")

    with open(inp_path, newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        rows = list(r)
        fieldnames = r.fieldnames or []

    results = []
    for row in rows:
        res = assess_row(row)
        merged = {**row, **{k: str(v) for k, v in res.items()}}
        results.append(merged)

    # union fieldnames
    all_keys: set = set()
    for rr in results:
        all_keys.update(rr.keys())
    # keep original first
    extra = sorted(k for k in all_keys if k not in fieldnames)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(fieldnames) + extra)
        w.writeheader()
        w.writerows(results)
    return results


def build_parser():
    p = argparse.ArgumentParser(prog="vaccine_coverage", description="Vaccine Coverage Estimator")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("single", help="single calculation")
    s.add_argument("--json", help='JSON of inputs e.g. bil')
    s.add_argument("--bili", type=float)
    s.add_argument("--creat", type=float)
    s.add_argument("--inr", type=float)
    s.add_argument("--na", type=float)
    s.add_argument("--qt", type=float)
    s.add_argument("--rr", type=float)
    s.add_argument("--hr", type=float)
    b = sub.add_parser("batch", help="batch csv")
    b.add_argument("--input", required=True)
    b.add_argument("--output", required=True)
    return p


def main(argv=None):
    p = build_parser()
    a = p.parse_args(argv)
    if a.cmd == "single":
        if a.json:
            row = json.loads(a.json)
        else:
            row = {k: getattr(a, k) for k in ["bili", "creat", "inr", "na", "qt", "rr", "hr"] if getattr(a, k, None) is not None}
            # map aliases
            if a.bili is not None:
                row["bilirubin"] = a.bili
            if a.creat is not None:
                row["creatinine"] = a.creat
            if a.inr is not None:
                row["inr"] = a.inr
            if a.na is not None:
                row["sodium"] = a.na
            if a.qt is not None:
                row["qt_ms"] = a.qt
            if a.rr is not None:
                row["rr_ms"] = a.rr
            if a.hr is not None:
                row["hr_bpm"] = a.hr
        print(assess_row(row))
        return 0
    if a.cmd == "batch":
        res = process_csv(a.input, a.output)
        print(f"Processed {len(res)} -> {a.output}")
        return 0
    p.print_help()
    return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
