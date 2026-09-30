# Architecture Specification — Returns Manager
**Cube Buildathon 04 · Round 2 Individual Build**

## System Architecture

```text
┌────────────────────────────────────────────────────────┐
│             Warehouse Returns Intake UI                │
│    (Static Client / Operator Terminal Dashboard)       │
└───────────────────────────┬────────────────────────────┘
                            │ HTTP POST /api/v1/returns/assess
                            │ Headers: X-Org-Id: org_demo_alpha
┌───────────────────────────▼────────────────────────────┐
│                    FastAPI Backend                     │
│  - Multi-tenant routing                                │
│  - Pydantic schema validation                          │
│  - Org-isolated image persistence                      │
└───────────────────────────┬────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              │                           │
┌─────────────▼───────────────┐ ┌─────────▼──────────────────────────┐
│  Batched Multimodal Agent   │ │   Catalogue & Authoritative Rules   │
│  - Single call for:         │ │   - Amazon Condition Scale (JSON)  │
│    • Identity Check         │ │   - Expected parts list            │
│    • Completeness Check     │ └────────────────────────────────────┘
│    • Condition Assessment   │
│  - Configurable GEMINI_MODEL│
│  - First-class UNCERTAIN    │
└─────────────┬───────────────┘
              │
┌─────────────▼──────────────────────────────────────────┐
│      Deterministic Disposition Rules Engine            │
│  - Pure Python business logic                          │
│  - Maps condition grade -> restock / refurbish /       │
│    liquidate / dispose / pending_review                │
│  - Fail-Open handling on LLM/Dependency failure        │
└─────────────┬──────────────────────────────────────────┘
              │
┌─────────────▼──────────────────────────────────────────┐
│          Structured Evidence Record Builder            │
│  - Canonical Evidence JSON Contract                    │
│  - SHA-256 Content Fingerprint                         │
│  - Latency and Model Version provenance metadata       │
└─────────────┬──────────────────────────────────────────┘
              │
┌─────────────▼──────────────────────────────────────────┐
│           Multi-Tenant SQLite / Database               │
│  - `return_records` partitioned strictly by org_id     │
│  - `overrides` append-only audit trail preserving      │
│     original vs revised verdicts and human reasons     │
│  - `images` registry with non-guessable tenant paths   │
└────────────────────────────────────────────────────────┘
```

## Components

1. **Intake & Assessment Router (`src/ingestion/router.py`)**:
   - Exposes RESTful endpoints (`POST /assess`, `GET /{record_id}`, `POST /{record_id}/override`, `GET /images/{image_id}`).
   - Gated by mandatory `X-Org-Id` tenant isolation header.

2. **Multimodal Agent (`src/agent/analyzer.py` & `prompt_builder.py`)**:
   - Manages Gemini API integration with dynamic model selection (`GEMINI_MODEL`).
   - Batches identity, completeness, and condition evaluation into a single visual prompt.
   - Includes deterministic mock engine for zero-cost offline evaluations.

3. **Authoritative Catalogue & Condition Scale (`src/catalogue/`)**:
   - Loads versioned Amazon Used Condition Guidelines from `config/condition_scale.json`.
   - Resolves bill-of-materials (BOM) parts lists for known SKUs.

4. **Deterministic Disposition Engine (`src/decisions/disposition_rules.py`)**:
   - Pure Python business logic mapping condition grades and completeness status to operational routings (`restock`, `refurbish`, `liquidate`, `dispose`, `pending_review`).
   - Completely decoupled from LLMs to ensure reproducible, explainable decisions.

5. **Structured Evidence Contract Assembler (`src/evidence/contract.py` & `hasher.py`)**:
   - Formats outputs to the official CUBE schema.
   - Generates SHA-256 fingerprint (`content_hash`) of the entire evaluation record.

6. **Tenant-Partitioned Database & Storage (`src/database/` & `src/images/storage.py`)**:
   - SQLAlchemy ORM with SQLite WAL mode.
   - Compound indexes on `(org_id, record_id)` and `(org_id, unit_id)`.
   - Append-only `overrides` table preserving full audit history.
   - Org-scoped image filesystem directories preventing path traversal attacks.

---

## Data Flow

```text
1. Warehouse Intake Request (POST /assess)
   ├── Tenant Header: X-Org-Id: org_demo_alpha
   └── Payload: unit_id, order_id, ordered_sku, parts_list, observed_state, images[]
         │
2. Tenant Storage & Validation
   ├── Store image bytes under storage/images/{org_id}/
   └── Look up expected parts BOM from catalogue
         │
3. Single Batched AI Vision Call
   ├── Sends images + item metadata + Amazon condition scale in one prompt
   └── Receives JSON: {identity: PASS/FAIL/UNCERTAIN, completeness: ..., condition: ...}
         │
4. Deterministic Disposition Resolution
   ├── Pure Python decision tree evaluates checks & Amazon condition scale
   └── Resolves disposition: restock / refurbish / liquidate / dispose / pending_review
         │
5. Evidence Contract Assembly & Fingerprinting
   ├── Wraps checks, outcomes, latencies, model version, and timestamps
   └── Computes SHA-256 canonical hash
         │
6. Multi-Tenant DB Persistence
   ├── Inserts ReturnRecord with org_id isolation
   └── Returns ReturnRecordEvidence JSON response
         │
7. Optional Human Operator Override (POST /{record_id}/override)
   ├── Validates tenant ownership
   └── Appends override to audit ledger and updates evidence blob
```

---

## Model / Agent Usage

- **Model Selection**: Configured dynamically via `GEMINI_MODEL` (defaults to `gemini-1.5-flash`, with support for `gemini-1.5-pro` and `gemini-2.0-flash`).
- **Batched Reasoning**: All three physical assessments (Identity, Completeness, Amazon Condition Grade) are combined into a single multimodal prompt to minimize latency and API cost.
- **Strict Identity Prompting**: The agent looks for verifiable identifiers (barcodes, serial labels, ASIN tags). If photos show only visual likeness without a verifiable identifier, the prompt strictly commands the agent to output `UNCERTAIN` rather than a blind `PASS`.
- **Offline / Fallback Simulation**: In CI/CD or zero-credential environments, a deterministic fallback simulator generates realistic outcomes without failing the test suite.

---

## Important Engineering Decisions

1. **Batched Multimodal AI Analysis (Engineering Rule 2)**:
   Avoids serial expensive model calls. A single multimodal request evaluates identity, expected components, and physical condition concurrently.

2. **Decoupled Observed State vs. Official Condition Scale**:
   The operator's initial visual intake (`observed_state`: factory_sealed, opened_unused, signs_of_use, damaged, empty_box, uncertain) is recorded separately from the authoritative Amazon grading (`New`, `Like New`, `Very Good`, `Good`, `Acceptable`).

3. **Strict Tenancy Isolation (Engineering Rule 1)**:
   All database access layers enforce `org_id` parameter binding. Records, overrides, and storage paths are fully segregated between tenants (`org_demo_alpha` and `org_demo_bravo`).

4. **Fail Open & First-Class Uncertainty (Engineering Rules 3 & 4)**:
   `UNCERTAIN` is treated as a valid first-class outcome, never converted to a false PASS or FAIL. Any model exception or timeout preserves all input data into `pending_review`.

5. **Append-Only Operator Overrides (Evidence Rule 3)**:
   When human inspectors disagree with agent decisions, an override record is appended with original verdict, revised verdict, operator ID, timestamp, and justification. The original AI verdict is never erased.
