# Cube Buildathon · 04 · Returns Manager

**Round 2 · Individual Build Submission**

> Five agents, one unit, one record that follows it.  
> Step 4 of 5: Customer return — condition, completeness, identity, and disposition.

---

## Problem Understanding

In high-volume e-commerce and 3PL returns operations, handling returns presents significant challenges:
- **Return Fraud & Switch Fraud**: Customers returning counterfeit, replica, or mismatched items in original boxes.
- **Subjective Inspection**: Human operators apply inconsistent condition criteria, resulting in misrouted inventory and customer friction.
- **Lack of Auditability**: Decisions lack structured, verifiable evidence trails that downstream systems (like Recovery or Claims Management) can trust.
- **Tenant Privacy**: 3PL prep centers serve multiple competing merchant organizations whose return records and photographic evidence must never cross boundaries.

The **04 · Returns Manager** addresses this by acting as an autonomous, auditable, and multi-tenant return inspection agent that standardizes condition grading, prevents fraudulent acceptances, and produces canonical evidence records for downstream systems.

---

## Solution Overview

When a customer return package arrives at the inspection station:
1. **Identity Verification**: Verifies returned product against the expected SKU/ASIN. Enforces strict verification: if photos lack machine-readable identifiers (barcodes, serial tags, ASIN stickers), the agent refuses to blindly PASS on visual likeness alone and safely marks `UNCERTAIN`.
2. **Completeness Verification**: Compares visible product contents against expected bill-of-materials components.
3. **Condition Assessment**: Evaluates physical wear against authoritative, published **Amazon Condition Guidelines** (`New`, `Like New`, `Very Good`, `Good`, `Acceptable`) loaded from versioned configuration.
4. **Deterministic Disposition Rules**: Computes routing recommendations (`restock`, `refurbish`, `liquidate`, `dispose`, or `pending_review`) using pure Python business logic without unvetted secondary LLM calls.
5. **Auditable Evidence Contract**: Produces a standardized, SHA-256 fingerprinted JSON record consumable downstream by Round 3 agents (e.g. Recovery Manager).

---

## Setup Instructions

### 1. Prerequisites
- Python 3.10+ (Tested on Python 3.12)
- Git

### 2. Clone and Install Dependencies
```bash
git clone https://github.com/jeevanreddy29/cube-04-returns-manager.git
cd cube-04-returns-manager
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Key configuration settings:
- `GEMINI_API_KEY`: Google Gemini API key (optional: if omitted, system runs in deterministic simulated evaluation mode).
- `GEMINI_MODEL`: Model identifier (default: `gemini-1.5-flash`; configurable to `gemini-1.5-pro` or `gemini-2.0-flash`).
- `DATABASE_URL`: SQLAlchemy connection string (default: SQLite `sqlite:///./returns_manager.db`).

---

## Usage Instructions

### Running the Application Locally
```bash
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```
- **Web UI & Operator Dashboard**: Visit [http://localhost:8000](http://localhost:8000)
- **Interactive OpenAPI Documentation**: Visit [http://localhost:8000/docs](http://localhost:8000/docs)

### Cloud Deployment
The application is live and publicly accessible on Vercel:
**[https://cube-04-returns-manager.vercel.app/](https://cube-04-returns-manager.vercel.app/)**

---

## Assumptions & Limitations

### Assumptions
1. **Upstream Catalog Data**: Expected SKU, ASIN, and parts BOM are assumed to be provided by the warehouse management system (WMS) or resolved from catalog configuration.
2. **First-Class Uncertainty**: When evidence is obscured, blurry, or missing serial identifiers, the agent deliberately treats `UNCERTAIN` as a valid outcome that routes to `pending_review` rather than guessing.
3. **Append-Only Override Policy**: Human operators have the authority to override AI verdicts, but the original verdict and justification must remain permanently recorded for auditability.

### Limitations
1. **Serverless Ephemeral Storage**: On serverless environments (Vercel), SQLite and file storage run in `/tmp`, which is ephemeral across cold boots. For production scale, an external PostgreSQL and S3-compatible object store should be configured.
2. **Visual Barcode Resolution**: Ultra-low-resolution photos (< 300 DPI) or severe lighting glare may prevent automated barcode reading, intentionally triggering an `UNCERTAIN` verdict.
3. **No Standalone Fraud Claiming**: Returns Manager flags evidence of mismatch/damage, but final financial claims/reimbursements are explicitly delegated downstream to the Recovery Manager.

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
