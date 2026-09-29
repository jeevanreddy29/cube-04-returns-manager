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

## Key Architectural Principles

1. **Batched Multimodal AI Analysis (Engineering Rule 2)**:
   Avoids serial expensive model calls. A single multimodal request evaluates identity, expected components, and physical condition concurrently.

2. **Decoupled Observed State vs. Official Condition Scale**:
   The operator's initial visual intake (`observed_state`: factory_sealed, opened_unused, signs_of_use, damaged, empty_box, uncertain) is recorded separately from the authoritative Amazon grading (`New`, `Like New`, `Very Good`, `Good`, `Acceptable`).

3. **Strict Tenancy Isolation (Engineering Rule 1)**:
   All database access layers enforce `org_id` parameter binding. Records, overrides, and storage paths are fully segregated between tenants (`org_demo_alpha` and `org_demo_bravo`).

4. **Fail Open & First-Class Uncertainty (Engineering Rules 3 & 4)**:
   `UNCERTAIN` is treated as a valid first-class outcome, never converted to a false PASS or FAIL. Any model exception or timeout preserves all input data into `pending_review`.

5. **Append-Only Operator Overrides (Evidence Rule 3)**:
   When human inspectors disagree with agent decisions, an override record is appended with original verdict, revised verdict, operator ID, timestamp, and justification.
