# Beaver's Choice Project Requirements

## Source register

| Source | Authority | Coverage | Status |
|---|---|---|---|
| `../The Beaver.docx` | Primary assignment and rubric | Project instructions, submission rules, all rubric tables | Read in full and visually inspected after rendering |
| `STARTER_README.md` | Udacity starter guidance | Setup, supplied data, execution expectations | Read in full |
| `project_starter.py` | Starter-code contract | Database schema, seven required helpers, evaluation stub | Read in full |
| `quote_requests_sample.csv` | Evaluation fixture | 20 dated customer requests | Schema and all rows inspected |
| `quote_requests.csv`, `quotes.csv` | Historical seed data | 100 paired requests and quotes | Schemas and representative rows inspected |
| `COMPARATIVE_REVIEW.md` | Advisory only | Public-project conventions and risks | Completed; no source material copied |

Authority order: the assignment rubric overrides the prompt narrative, which overrides starter guidance and code conventions. Public repositories are advisory only.

## Architecture decision

The implementation uses Pydantic AI with four agents: an orchestrator, inventory agent, quote agent, and sales agent. Four agents are enough to keep responsibilities distinct while staying below the five-agent limit. The business rules and database mutations remain deterministic so the supplied evaluation can be reproduced without depending on model variability. Pydantic AI supplies the agent definitions and framework-native tool registrations. When a valid `UDACITY_OPENAI_API_KEY` is available, the same agents can be configured for Udacity's OpenAI-compatible endpoint.

Pydantic AI was selected because its typed agents, framework-native tools, programmatic agent delegation, custom OpenAI-compatible provider, and deterministic `FunctionModel` fit the assignment's reliability and explainability requirements. The dependency is pinned in `requirements.txt` after checking the current package release and official documentation.

## Starter helper descriptions and ownership

| Helper | Purpose | Agent tool ownership |
|---|---|---|
| `create_transaction` | Record a stock purchase or completed sale in the transaction ledger. | Sales agent |
| `get_all_inventory` | Return all positive stock balances as of a date. | Inventory agent |
| `get_stock_level` | Calculate available units for one catalog item as of a date. | Inventory agent |
| `get_supplier_delivery_date` | Estimate replenishment arrival from the request date and quantity. | Inventory agent |
| `get_cash_balance` | Calculate cash after sales revenue and inventory purchases. | Sales agent |
| `generate_financial_report` | Produce cash, inventory value, assets, inventory detail, and top sellers. | Orchestrator agent |
| `search_quote_history` | Retrieve relevant historical requests and prices to support a quote. | Quote agent |

## Rubric-to-artifact matrix

| ID | Exact requirement | Type | Artifact | Validation/evidence | Status |
|---|---|---|---|---|---|
| R1 | No more than five agents | Structure | `project_starter.py`, diagram | Static test confirms four Pydantic AI agent instances | Verified |
| R2 | Text-only input and output | Behavior | `project_starter.py` | Unit tests and complete sample execution | Verified |
| R3 | Diagram shows every agent, distinct role, orchestration, and data flow | Evidence | `workflow_diagram.png` | Full-resolution visual inspection | Verified |
| R4 | Diagram maps each tool to its purpose and starter helper | Evidence | `workflow_diagram.png` | Rubric inspection of all tool/helper labels | Verified |
| R5 | Orchestrator delegates inventory, quoting, and sales work | Structure/behavior | `project_starter.py` | Orchestrator tool registration and workflow tests | Verified |
| R6 | Use Pydantic AI, smolagents, or npcsh | Structure | `project_starter.py`, `requirements.txt` | Import, pinned dependency, and agent-definition test | Verified |
| R7 | Every required starter helper appears in a framework-defined tool | Structure | `project_starter.py` | Tool-registration source inspection and automated test | Verified |
| R8 | Inventory agent answers stock questions and assesses replenishment timing | Behavior | `project_starter.py` | Stock, shortage, and supplier-timing tests | Verified |
| R9 | Quote agent uses historical data and strategic discounts | Behavior | `project_starter.py` | Quote-history and discount-boundary tests | Verified |
| R10 | Sales agent finalizes only feasible orders and updates the database | Behavior | `project_starter.py` | Rejection atomicity plus stock and cash mutation tests | Verified |
| R11 | Evaluate every row in `quote_requests_sample.csv` | Evidence | `test_results.csv` | 20 rows and 20 unique request IDs confirmed | Verified |
| R12 | At least three fulfilled requests and three cash changes | Evidence | `test_results.csv` | 9 fulfilled requests and 9 cash changes | Verified |
| R13 | At least one request remains unfulfilled with a clear reason | Evidence | `test_results.csv` | 11 rejected requests, each with a reason | Verified |
| R14 | Customer output is complete, reasoned, and excludes margins, internals, and unnecessary PII | Quality | `project_starter.py`, `test_results.csv` | Content assertions, Request 4 line-preservation regression, prohibited-string checks, and clean runtime output | Verified |
| R15 | Submit one Python implementation file | Submission | `project_starter.py` | Submission inventory contains one `.py` file; development tests remain outside | Verified |
| R16 | Report explains architecture, results, strengths, and at least two improvements | Evidence | `reflective_report.docx` | Six-page render and page-by-page visual inspection | Verified |
| R17 | Code is readable, appropriately documented, and modular within the single-file constraint | Quality | `project_starter.py` | Source review, compilation, dependency check, and 18 passing tests | Verified |

## Evaluator feedback resolution

| Feedback | Requirement | Reproduction | Focused change | Regression evidence | Target | Status |
|---|---|---|---|---|---|---|
| Request 4 confirmed only cardstock and silently omitted 250 sheets of printer paper. | Preserve every requested line through parsing and response generation. | The parser returned only `Cardstock, 500` for the supplied Request 4 wording. | Recognize `along with` as a separator between quantified order lines without changing the agent architecture. | The focused regression first failed with the missing line, then passed; refreshed row 4 now confirms both `500 Cardstock` and `250 Standard copy paper`. | Public `main` | Verified and included in the corrective `main` update. |

## Key implementation assumptions

- Requests containing unsupported products or ambiguous quantities are rejected rather than guessed.
- A request is fulfilled only if every requested line can be supplied by its deadline; partial sales are not recorded.
- Replenishment is considered only when the catalog item exists, the company has enough cash, and the supplier can deliver before the customer deadline.
- Reams are normalized to 500 sheets only for paper products. Other package terms are rejected when their unit conversion is unspecified.
- Discounts apply to customer totals, never to internal inventory cost, and customer messages do not disclose margins or database details.
