# Cube Buildathon · 04 · Returns Manager

**Round 2 · Individual Build Submission**

> Five agents, one unit, one record that follows it.  
> Step 4 of 5: Customer return — condition, completeness, identity, and disposition.

---

## Overview

The **Returns Manager** is an autonomous and auditable inspection system designed for e-commerce merchants and prep centers. When a customer return package arrives, this agent performs:

1. **Identity Verification**: Verifies returned product matches the ordered ASIN/SKU.
2. **Completeness Verification**: Compares visible package contents against the bill of materials / expected parts list.
3. **Condition Assessment**: Evaluates physical wear using the authoritative, published **Amazon Condition Guidelines** (`New`, `Like New`, `Very Good`, `Good`, `Acceptable`).
4. **Deterministic Disposition**: Computes routing recommendations (`restock`, `refurbish`, `liquidate`, `dispose`, or `pending_review`).
5. **Auditable Evidence Contract**: Produces a standardized, SHA-256 fingerprinted JSON record consumable downstream by Recovery Manager.

---

## Key Engineering Compliance

- **Batched Multimodal AI Execution (Engineering Rule 2)**: All visual reasoning (identity, completeness, condition) is performed in a **single batched Gemini multimodal call**, preventing expensive serial invocations.
- **Configurable Model**: Configurable dynamically via `GEMINI_MODEL` (e.g. `gemini-1.5-flash`, `gemini-1.5-pro`, `gemini-2.0-flash`).
- **Decoupled Observed State vs. Official Scale**: Raw operator observations (`observed_state`) are kept distinct from official Amazon grades (`amazon_condition`).
- **First-Class Uncertainty (Engineering Rule 4)**: `UNCERTAIN` is an explicit, supported verdict. The agent never forces ambiguous visual evidence into false binary outcomes.
- **Fail Open (Engineering Rule 3)**: Any model timeout or dependency error preserves all data and routes the case to `pending_review`.
- **Append-Only Operator Overrides (Evidence Rule 3)**: Disagreements by human inspectors are stored in an append-only ledger preserving original vs. revised decisions with reasons.
- **Strict Tenancy Isolation (Engineering Rule 1)**: Built-in multi-tenant isolation enforcing `org_id` boundaries on all database queries and image access.

---

## Quickstart

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
Copy the `.env.example` file:
```bash
cp .env.example .env
```
Add your `GEMINI_API_KEY` (if testing with live Google Gemini models). When left blank, the application automatically runs in deterministic mock evaluation mode.

### 3. Run the Application
```bash
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```
- **Web UI & Operator Dashboard**: Visit [http://localhost:8000](http://localhost:8000)
- **Interactive OpenAPI Documentation**: Visit [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Running the Automated Test Suite

Execute unit tests and integration tests covering normal flows, ambiguous cases, fail-open behavior, and tenant isolation:
```bash
python -m pytest tests -v
```

---

## Evaluation Benchmark

The evaluation suite tests an independent 50-unit held-out dataset annotated with dual independent human reviews:
```bash
python eval/run_eval.py
```
Detailed results are stored in `eval/eval_report.md`.

---

## Project Structure

```text
cube-04-returns-manager/
├── config/
│   └── condition_scale.json        # Authoritative Amazon condition guidelines
├── data/
│   ├── README.md
│   └── returns_sample.csv          # Synthetic development sample
├── eval/
│   ├── labelled_holdout.csv        # 50-unit held-out benchmark with dual labels
│   ├── run_eval.py                 # Evaluation benchmark script
│   └── eval_report.md              # Generated accuracy & latency metrics
├── src/
│   ├── agent/                      # Batched Gemini vision analyzer & prompt builder
│   ├── catalogue/                  # Amazon condition scale & parts catalog
│   ├── database/                   # Multi-tenant SQLite ORM & repository
│   ├── decisions/                  # Deterministic Python disposition engine
│   ├── evidence/                   # Evidence contract assembler & SHA-256 hasher
│   ├── images/                     # Tenant-isolated image storage
│   ├── ingestion/                  # FastAPI router & Pydantic schemas
│   ├── config.py                   # Pydantic settings & dynamic model configuration
│   └── main.py                     # FastAPI application entry point
├── tests/
│   ├── integration/                # Tenant isolation & fail-open integration tests
│   └── unit/                       # Disposition & condition scale unit tests
├── ui/public/index.html            # Operator demo dashboard
├── ARCHITECTURE.md                 # System architecture specification
├── requirements.txt
└── .env.example
```
