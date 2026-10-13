# Vaccine Coverage Estimator

Population immunization coverage, two-sided 95% Wilson score interval, and optional dose-series dropout. The original clinical calculators and agent interfaces remain for compatibility.

## Browser application

Open `web/index.html` in a recent browser, or serve it locally:

```bash
python -m http.server 8000 --directory web
```

Enter eligible-population and vaccinated-person counts, then select **Calculate coverage**. For dose-series dropout, provide both first- and final-dose counts from the same cohort. The CSV tool accepts required `population` and `vaccinated` columns, plus optional `group`, `first_dose`, and `final_dose`. Download the sample CSV from the app and export the results as CSV.

Browser calculations and CSV processing use local JavaScript; no server, Python runtime, external scripts, analytics, or data upload is required.

## Methods and constraints

- Coverage (%) = 100 × vaccinated people / eligible population.
- The confidence interval is the two-sided **Wilson score interval** for a binomial proportion (95% confidence).
- Dropout (%) = 100 × (first-dose count − final-dose count) / first-dose count; undefined if no first doses were recorded.

Counts must be whole numbers. Population must be greater than zero, vaccinated and first-dose counts must not exceed population, and final-dose counts must not exceed first-dose counts. Cohort and reporting period definitions must be consistent.

**Limitations:** Wilson intervals do not account for ascertainment bias, inaccurate denominator estimates, repeat doses, clustering, or registry incompleteness. Population census coverage is descriptive rather than a sample estimate. This calculator is not a clinical decision-support tool.

## Python CLI and API

Install Python 3.10+ and the package:

```bash
python -m pip install -e ".[dev]"
python cli.py coverage --population 1000 --vaccinated 850 --first-dose 900 --final-dose 810
python -m vaccine_coverage single --json '{"population":1000,"vaccinated":850}'
python -m vaccine_coverage batch --input web/sample.csv --output results.csv
```

Import the same calculation directly:

```python
from immunization import estimate_coverage
print(estimate_coverage(1000, 850, 900, 810))
```

An optional local FastAPI service is available through `python cli.py serve`. Its `POST /api/coverage` endpoint accepts a JSON object with `population`, `vaccinated`, and optional dose counts. The original `audit`, `batch`, `chat` commands, audit API, and legacy clinical calculators remain available but are **not validated clinical decision-support algorithms**.

## Testing

```bash
python -m pytest
node --check web/app.js
node --test tests_js/*.test.cjs
```

CI tests Python 3.10–3.12 and Node 22. The static app uses features supported in modern Chrome, Firefox, and Safari.

## Privacy and security

The browser app processes aggregate counts locally. Do not upload patient-level identifiable data. The local API has no built-in authentication; bind it to localhost or put it behind an authenticated gateway. The API's identifier regex guard is **not** a reliable de-identification system.

For Docker, create a private persistent key before starting the container:

```bash
export AUDIT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
docker compose up --build
```

Rotate any key previously copied from public examples. The audit ledger is in memory and is lost on restart even when the signing key is persistent.

## License

MIT — see [LICENSE](LICENSE).
