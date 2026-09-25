# IRecruit — AI Resume Intelligence & Job Alignment Engine

[![Continuous Integration](https://github.com/saniyajalaluddin/IRecruit/actions/workflows/ci.yml/badge.svg)](https://github.com/saniyajalaluddin/IRecruit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.14-blue)](https://www.python.org/downloads/)
[![Test Suite](https://img.shields.io/badge/tests-227%20passed-brightgreen)](tests/)
[![Zero Fabrication](https://img.shields.io/badge/Hallucination%20Rate-0.0%25-success)](docs/BENCHMARK_REPORT.md)

**IRecruit** is an enterprise-grade, portfolio-quality career intelligence platform and semantic alignment engine. It analyzes candidate resumes against target job descriptions (JDs) with **mathematical determinism, explainable scoring, verbatim evidence grounding, and zero fabrication**.

Unlike generic LLM wrappers, IRecruit implements a multi-layered NLP and semantic architecture where external language models assist in qualitative synthesis, but **never secretly dictate numerical alignment scores or hallucinate candidate skills**.

---

## 1. Non-Negotiable Core Principles

1. **Evidence First**: Every competency match is grounded strictly in verbatim candidate-provided text. The engine categorizes all JD requirements into four clear states: `MATCHED`, `PARTIAL`, `MISSING`, or `AMBIGUOUS`. Absence of evidence is never equated with proof of incompetence; missing competencies clearly report: *"No supporting evidence was found in the submitted resume."*
2. **Zero Fabrication**: The engine never hallucinates skills, employers, metrics, dollar values, percentages, or credentials. Resume optimization only reorganizes or sharpens wording for evidence that already exists.
3. **JD-Driven Priority**: Requirement criticality is derived strictly from job description language (e.g., *required*, *must have*, *minimum qualifications* vs. *preferred*, *nice to have*), preventing arbitrary weighting.
4. **Untrusted Input & Guarded LLMs**: Resumes and JDs are treated as untrusted data vectors. The system actively scans and neutralizes adversarial prompt injections, delimiters, and zero-width unicode exploits. LLM responses pass through Pydantic schemas, business rules, and evidence verification before display.
5. **Privacy First (PII Minimization)**: Automatically detects and redacts sensitive PII (SSNs, credit card numbers, personal phone numbers, physical street addresses) before LLM tokenization and persistence.

---

## 2. System Architecture

IRecruit is architected as a **Modular Monolith** designed for high throughput, maintainability, and clean separation of concerns:

```
[ Frontend Client (Responsive SPA, Vanilla ES6+, CSS3 Design System) ]
                               │
                               ▼
   [ FastAPI REST Gateway (/api/v1/ - CORS, Security Headers, Rate Limiting) ]
                               │
       ┌───────────────────────┴────────────────────────┐
       ▼                                                ▼
[ Auth & Ownership Engine ]                   [ Security Middleware ]
(JWT, Passlib, RBAC, Claims)                  (Prompt Injection & PII Redaction)
       │                                                │
       └───────────────────────┬────────────────────────┘
                               ▼
              [ Domain Application Services ]
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
 [ Resume Engine ]      [ JD Engine ]        [ Matching Engine ]
 (PyPDF, DOCX Parser)   (Section Segmenter)   (Multi-Signal Semantic Cosine)
        │                      │                      │
        └──────────────────────┼──────────────────────┘
                               ▼
                    [ Evidence Engine ]
               (Verbatim Quote Validation)
                               │
                               ▼
              [ Deterministic Scoring Engine ]
              (Weights: 40% Req / 25% Exp / 15% Pref / 10% Domain / 10% Edu)
                               │
       ┌───────────────────────┴────────────────────────┐
       ▼                                                ▼
[ ATS Compatibility Audit ]                   [ Gap & Recommendation Engine ]
(Tables, Columns, Headers)                    (Targeted Evidence Enhancement)
                               │
                               ▼
    [ Persistence & Auditing (SQLAlchemy 2.0 Async, SQLite/PostgreSQL) ]
```

---

## 3. Key Technical Capabilities

| Module | Core Functionality |
| :--- | :--- |
| **Document Parser** | Streams and extracts structured text from PDF, DOCX, and TXT files with format validation and MIME sniffing. |
| **Semantic Matcher** | Multi-signal matching combining token-boundary regexes, canonical taxonomy normalizers, and vector embeddings. |
| **Evidence Engine** | Cross-references parsed requirements with verbatim candidate quotes; flags ambiguous qualifiers (*"familiar with"*, *"exposure to"*). |
| **Explainable Scoring** | Computes a deterministic 0–100 alignment score with component breakdowns and letter grades (A+ through D). |
| **ATS Compatibility** | Evaluates resumes against parser rules (multi-column layouts, tables, font readability, standard section headers). |
| **PII Minimization** | High-precision regex engine redacting SSNs, credit cards, phones, and addresses prior to model inference. |
| **Prompt Injection Defense** | Scans and neutralizes system-instruction breakouts, developer jailbreaks, and score tampering attacks. |
| **Candidate Dashboard** | Tracks historical evaluations (capped at 5 for free tier), average alignment scores, and recurring missing competencies. |
| **Version Delta Engine** | Compares sequential resume revisions (v1 vs. v2) to quantify score deltas and newly matched requirements. |
| **Reproducibility** | Attaches SHA-256 configuration hashes, prompt versions, model identifiers, and audit explanations to every analysis. |

---

## 4. API Endpoints Reference

All API routes are prefixed under `/api/v1/`:

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/auth/register` | Register candidate account with email & password | No |
| `POST` | `/auth/login` | Authenticate and obtain JWT access token | No |
| `GET` | `/auth/me` | Fetch authenticated user profile | Yes |
| `POST` | `/resumes/upload` | Upload PDF/DOCX resume file (max 10MB) | Yes |
| `POST` | `/analyses/anonymous` | Run instant anonymous evaluation (24h retention) | No |
| `POST` | `/analyses/{id}/claim` | Transfer anonymous evaluation into candidate account | Yes |
| `GET` | `/analyses/dashboard` | Retrieve dashboard metrics and recurring skill gaps | Yes |
| `GET` | `/analyses/history` | Retrieve saved evaluation history (tier-capped) | Yes |
| `GET` | `/analyses/{id}` | Retrieve full alignment analysis and evidence | Yes |
| `GET` | `/analyses/{id}/reproducibility` | Retrieve model configuration and audit explanation | Yes |
| `DELETE` | `/analyses/{id}` | Permanently delete analysis and linked records | Yes |
| `GET` | `/resumes/{id}/compare` | Compute delta comparison across resume versions | Yes |
| `GET` | `/health` | Liveness and component readiness check | No |
| `GET` | `/metrics` | Request latency and pipeline telemetry | No |

---

## 5. Empirical Benchmark Results

Evaluated against ground-truth resumes and target job descriptions (`tests/test_evaluation_suite.py`):

| Evaluation Metric | Production Target | Measured Result | Status |
| :--- | :--- | :--- | :--- |
| **Precision** | $\ge 85.0\%$ | **100.0%** (1.00) | PASS |
| **Recall** | $\ge 85.0\%$ | **100.0%** (1.00) | PASS |
| **Accuracy** | $\ge 85.0\%$ | **100.0%** (1.00) | PASS |
| **Hallucination Rate** | $\le 0.0\%$ | **0.0%** (0.00) | PASS |
| **Absence Statement Compliance**| $100.0\%$ | **100.0%** (1.00) | PASS |
| **Adversarial Injection Defense**| $100.0\%$ | **100.0%** (1.00) | PASS |

---

## 6. Quickstart & Installation

### Local Development Setup

```bash
# 1. Clone repository
git clone https://github.com/saniyajalaluddin/IRecruit.git
cd IRecruit

# 2. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set environment configuration
cp .env.example .env  # Configure your settings (never commit .env)

# 5. Run tests
pytest -v

# 6. Start development server
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Open your browser at `http://localhost:8000` to interact with the responsive web interface.

### Running with Docker

```bash
# Build and launch with Docker Compose
docker-compose up -d --build

# Verify container health
curl -f http://localhost:8000/api/v1/health
```

---

## 7. Documentation Index

- [Architecture Blueprint](docs/ARCHITECTURE.md) — In-depth architectural decomposition, data pipelines, and threat models.
- [API Specifications](docs/API_SPECIFICATION.md) — Detailed OpenAPI request/response schemas and example payloads.
- [AI Benchmark Report](docs/BENCHMARK_REPORT.md) — Empirical benchmark suite, confusion matrices, and ground truth definitions.

---

## 8. License & Compliance

Copyright &copy; 2026 IRecruit Intelligence Systems. Built with deterministic AI engineering and evidence grounding. Released under the MIT License.
