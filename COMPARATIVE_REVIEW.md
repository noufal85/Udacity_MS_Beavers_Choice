# Comparative GitHub Review

Public repositories were reviewed as observational references on October 25, 2026. No code, prose, assets, or repository structure was copied. The local assignment brief, rubric, starter code, and supplied data remain authoritative.

| Public reference | Useful practices observed | Decision for this project |
|---|---|---|
| https://github.com/ucaiado/agentic-order-system | Clear role separation, typed schemas, explicit test commands, reproducible entry points, and easy-to-find evidence. | Adopt clear responsibilities, typed request/decision models, deterministic tests, and a documented entry point. Do not adopt its multi-module, Docker, or notebook layout because the rubric requires one Python implementation file. |
| https://github.com/PHIacademy/agentic-ai-c4-multi-agent-systems-project | Keeps the required deliverables visible and documents how to run the complete evaluation. | Keep the diagram, implementation, evaluation CSV, and reflection easy to locate. Add stronger transaction-safety and deterministic validation evidence than the reference exposes. |
| https://github.com/yradwan147/nd900-p4-beavers-choice | Maps agents to tools and starter helpers and respects the five-agent limit. | Preserve explicit agent/tool/helper mapping. Do not reuse its 71-row evaluation assumption because the authoritative local fixture contains 20 rows, and provide the required image rather than only diagram source. |
| https://github.com/Melvin-Mora/Beavers-Choice-Paper-Company | Demonstrates a compact single-file implementation with supporting diagram and report artifacts. | Retain the compact submission shape, but exclude credentials and environment files, keep the evaluation deterministic, and document reproducible checks. |

## Best practices applied

- Four agents have non-overlapping responsibilities and remain below the five-agent limit.
- Pydantic models define the request and decision boundaries.
- Every starter helper is exposed through a framework-defined tool owned by an appropriate agent.
- Business mutations occur only after the complete request passes validation, inventory, timing, pricing, and cash checks.
- The full supplied sample is evaluated reproducibly, with results written to `test_results.csv`.
- The README provides setup, execution, validation, evidence, and secret-handling guidance.
- The submission excludes `.env`, virtual environments, caches, generated databases, and development-only tests.

## Practices intentionally not adopted

- Additional agents whose responsibilities would overlap existing roles.
- Multi-module or containerized architecture that conflicts with the single-Python-file constraint.
- Live-model dependence for rubric evaluation, which would make results variable and credential-dependent.
- External project assumptions about row counts, product conversions, inventory, or pricing.
- Customer responses that reveal margins, database details, stack traces, credentials, or unnecessary personal information.
