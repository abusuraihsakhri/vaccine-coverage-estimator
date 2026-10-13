"""Population vaccine coverage, Wilson confidence interval, and dose-series dropout.

Counts must represent people in one cohort and reporting period. A Wilson
interval quantifies binomial uncertainty, not registry or denominator bias.
"""
from statistics import NormalDist


def _count(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValueError(f"{name} must be a non-negative integer")
    try:
        number = int(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{name} must be a non-negative integer") from exc
    if number < 0 or (isinstance(value, str) and not value.isdecimal()):
        raise ValueError(f"{name} must be a non-negative integer")
    return number


def estimate_coverage(population, vaccinated, first_dose=None, final_dose=None, confidence=0.95):
    """Estimate vaccination coverage (percent), Wilson CI, and optional dropout.

    Cohort-aligned dose counts satisfy final_dose <= first_dose <= population.
    When no initial dose is recorded, dropout is undefined (None).
    """
    n = _count(population, "population")
    k = _count(vaccinated, "vaccinated")
    if n == 0:
        raise ValueError("population must be greater than zero")
    if k > n:
        raise ValueError("vaccinated cannot exceed population")
    try:
        level = float(confidence)
    except (TypeError, ValueError) as exc:
        raise ValueError("confidence must be strictly between 0 and 1") from exc
    if not 0 < level < 1:
        raise ValueError("confidence must be strictly between 0 and 1")
    if (first_dose is None) != (final_dose is None):
        raise ValueError("first_dose and final_dose must be supplied together")

    p = k / n
    z = NormalDist().inv_cdf((1 + level) / 2)
    z2 = z ** 2
    denom = 1 + z2 / n
    mid = (p + z2 / (2 * n)) / denom
    delta = z * (p * (1 - p) / n + z2 / (4 * n * n)) ** 0.5 / denom
    result = {
        "population": n,
        "vaccinated": k,
        "coverage_percent": round(100 * p, 2),
        "ci_lower_percent": round(100 * max(0.0, mid - delta), 2),
        "ci_upper_percent": round(100 * min(1.0, mid + delta), 2),
        "confidence": level,
        "dropout_percent": None,
    }
    if first_dose is not None:
        first = _count(first_dose, "first_dose")
        final = _count(final_dose, "final_dose")
        if first > n or final > first:
            raise ValueError("dose counts must satisfy final_dose <= first_dose <= population")
        result.update({
            "first_dose": first,
            "final_dose": final,
            "dropout_percent": round(100 * (first - final) / first, 2) if first else None,
        })
    return result
