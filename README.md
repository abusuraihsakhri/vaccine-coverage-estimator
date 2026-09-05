# Vaccine Coverage Estimator

> **Domain:** Clinical Decision Support & Biomedical Computing  
> **Reference Guidelines & Standards:** Standard Clinical Formulations & ISO/IEC Quality Frameworks

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

Vaccine Coverage Estimator provides clinical calculation utilities for lab value interpretation. It calculates coverage metrics, scores, and confidence intervals from immunization registry data, and includes specialized calculators for common clinical indices (MELD-Na, QTc, BMI, HbA1c, APRI/FIB-4).

---

## ⚙️ Key Capabilities & Algorithmic Modules

### 🔬 Clinical Calculation Functions

- **`calculate_score()`** — Generic formula: weighted sum of numeric inputs.
- **`calculate_meld_na()`** — MELD-Na score for liver disease severity (bilirubin, creatinine, INR, sodium).
- **`calculate_qtc()`** — QTc (corrected QT interval) using Bazett's formula.
- **`calculate_bmi_z()`** — BMI calculation with WHO classification and approximate z-score.
- **`convert_hba1c()`** — Bidirectional conversion between HbA1c (%) and estimated average glucose (mg/dL).
- **`calculate_apri_fib4()`** — APRI and FIB-4 scores for hepatic fibrosis assessment.

### 🔄 Data Processing

- **`assess_row()`** — Routes a data row to the appropriate clinical calculator based on present keys.
- **`process_csv()`** — Batch processes CSV files with path-traversal protection and input validation.

---

## 💻 Installation

```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/vaccine-coverage-estimator.git
cd vaccine-coverage-estimator

# Install dependencies
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"
```

---

## 🧪 Usage

### 1. Command Line Interface (Core Module)

```bash
# Single calculation with JSON input
python -m vaccine_coverage single --json '{"bilirubin": 2.0, "creatinine": 1.2, "inr": 1.5, "sodium": 135}'

# Batch CSV processing
python -m vaccine_coverage batch --input sample.csv --output results.csv
```

### 2. Enterprise CLI (with Agent System)

```bash
# Single task evaluation
python cli.py audit --task-id TASK-01 --primary 28.5 --secondary 14.2

# Batch processing
python cli.py batch -i input.csv -o output.csv

# Chat interface
python cli.py chat "Explain coverage metrics"

# Verify audit trail integrity
python cli.py verify-audit
```

### 3. FastAPI REST Server

```bash
python cli.py serve --host 127.0.0.1 --port 8000
```

Then visit:
- `http://localhost:8000/health` — Health check
- `http://localhost:8000/metrics` — Operational metrics
- `http://localhost:8000/docs` — Interactive API documentation

### 4. Python API

```python
from vaccine_coverage import assess_row, calculate_meld_na

# Route-based calculation
result = assess_row({"bilirubin": 2.5, "creatinine": 1.5, "inr": 1.8, "sodium": 132})
print(result)

# Direct calculator
meld = calculate_meld_na(bilirubin=2.5, creatinine=1.5, inr=1.8, sodium=132)
print(meld)
```

---

## 📐 Input Data Schema

### CSV Fields for `process_csv()`

The system automatically detects which calculator to use based on column names:

| Calculator | Required Fields | Optional Fields |
|:-----------|:----------------|:----------------|
| MELD-Na | `bilirubin`, `creatinine` | `inr`, `sodium`, `albumin`, `sex`, `dialysis` |
| QTc | `qt` or `qt_ms` | `rr_ms`, `hr_bpm` or `heart_rate` |
| BMI | `weight_kg`, `height_cm` | `age_months` or `age`, `sex` |
| HbA1c | `hba1c_percent` or `eag_mgdl` | — |
| APRI/FIB-4 | `ast_u_l` | `alt_u_l`, `platelets_109`, `age_years` |
| Generic Score | Any numeric fields | — |

### Sample CSV

```csv
id,value,qty
A,10,2
B,20,3
```

---

## 🛡️ Security & Enterprise Architecture

* **Zero-PHI Outbound Interceptor:** Active regex inspection blocking SSNs, MRNs, phone numbers, emails, and patient identifiers from outbound data.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation and state transition.
* **Path Traversal Protection:** Input/output file paths are validated to prevent directory traversal attacks.
* **Secure Defaults:** Audit keys are randomly generated per-session when `AUDIT_SECRET_KEY` is not set. Set this environment variable in production for persistent signature verification.

### Environment Variables

| Variable | Purpose | Required |
|:---------|:--------|:---------|
| `AUDIT_SECRET_KEY` | HMAC-SHA256 signing key for audit trail | Recommended (production) |
| `MODEL_PROVIDER` | LLM provider selection (`mock`, `ollama`, `openai`, etc.) | No (default: mock) |

---

## 🧪 Testing & Verification

Run the complete test suite:

```bash
pytest -v
```

Run with coverage:

```bash
pytest --cov=. --cov-report=term-missing
```

Execute high-throughput batch simulation benchmarks:

```bash
python simulator.py --tasks 1000 --concurrency 8
```

---

## 🐳 Container Deployment

```bash
docker build -t vaccine-coverage-estimator .
docker run -p 8000:8000 -e AUDIT_SECRET_KEY=your-secret-key vaccine-coverage-estimator
```

Or with Docker Compose:

```bash
docker-compose up -d
```

---

## 📁 Project Structure

```
vaccine-coverage-estimator/
├── vaccine_coverage.py     # Core calculation module (stdlib only)
├── cli.py                  # Enterprise CLI with agent system
├── simulator.py            # High-throughput simulation benchmarks
├── enrichment.py           # Feature enrichment engines
├── pyproject.toml          # Project metadata and dependencies
├── agents/                 # Enterprise agent system
│   ├── supervisor.py       # Multi-worker orchestrator
│   ├── workers.py          # Specialized domain workers
│   ├── base.py             # Security, PHI guard, audit trail
│   ├── models.py           # Pydantic data schemas
│   ├── api.py              # FastAPI REST endpoints
│   ├── metrics.py          # Prometheus metrics exporter
│   ├── learning.py         # Bayesian calibration engine
│   ├── llm_factory.py      # LLM provider abstraction
│   └── streamer.py         # WebSocket telemetry broadcaster
├── tests/                  # Test suite
│   ├── test_calculations.py
│   ├── test_enrichment.py
│   └── test_vaccine_coverage_estimator.py
├── web/index.html          # Operations console UI
└── Dockerfile              # Container build configuration
```

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
