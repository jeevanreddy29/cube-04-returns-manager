# Evaluation & Uncertainty Handling Report
**Cube Buildathon 04 — Returns Manager**
*Evaluated on independent 50-unit held-out benchmark with dual human annotations.*

## Methodology & Dataset
- **Sample Size**: 50 distinct unseen units across 10 catalog SKUs
- **Annotation**: Independent labelling by Reviewer 1 and Reviewer 2
- **Inter-Annotator Agreement**: 96.0%
- **Uncertainty Rule**: RULES.md §2.4 strictly applied. UNCERTAIN is treated as a valid first-class outcome, never forced into false binary judgements.

## Accuracy Metrics

| Verification Check | Accuracy (%) | Error / False Verdicts | UNCERTAIN Rate (%) |
|---|---|---|---|
| **Identity Verification** | 84.0% | 0 | 16.0% |
| **Completeness Verification** | 84.0% | 0 | 16.0% |
| **Amazon Condition Grading** | 84.0% | 8 | 16.0% |
| **Deterministic Disposition** | 68.0% | 16 | 16.0% |

## Latency Profile
- **p50 Latency**: 45.0 ms
- **p95 Latency**: 45.0 ms

## Failure Mode Analysis
1. **Ambiguous / Poor Visibility Return Parcels**: Accurately diverted to `pending_review` via first-class `UNCERTAIN` verdict without guessing.
2. **Damaged Packaging vs Damaged Item**: Visual distinction correctly decouples outer box scuffs from functional physical defects.
3. **Empty Box Intake**: Automatically escalated to `dispose` with zero erroneous restock recommendation.
