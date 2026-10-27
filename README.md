# Beaver's Choice Paper Company Multi-Agent System

This project implements a four-agent inventory, quoting, and sales workflow for Beaver's Choice Paper Company. It executes the orchestrator and worker agents through Pydantic AI while keeping the business rules deterministic for reproducible evaluation.

## Deliverables

- `project_starter.py` - the complete single-file implementation
- `workflow_diagram.png` - agents, orchestration, data flow, tools, purposes, and starter-helper mappings
- `test_results.csv` - results from all 20 supplied evaluation requests
- `reflective_report.docx` - architecture, design decisions, evaluation analysis, limitations, and improvements

Supporting project notes are in `PROJECT_REQUIREMENTS.md` and `COMPARATIVE_REVIEW.md`.

## Architecture

The system stays below the five-agent limit with four non-overlapping roles:

1. The orchestrator parses and validates each request, delegates work, and composes the customer response.
2. The inventory agent checks stock, calculates shortages, and verifies supplier timing.
3. The quote agent checks historical quote context and applies consistent volume discounts.
4. The sales agent checks available cash and records approved replenishment and sales transactions.

All seven required starter helpers are registered through Pydantic AI tools:

- `create_transaction`
- `get_all_inventory`
- `get_stock_level`
- `get_supplier_delivery_date`
- `get_cash_balance`
- `generate_financial_report`
- `search_quote_history`

## Setup

Python 3.10 or newer is required. Python 3.13 was used for the verified run.

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

The evaluation is deterministic and does not require an API credential. To configure the agents for Udacity's OpenAI-compatible endpoint, set the key only in the environment:

```bash
export UDACITY_OPENAI_API_KEY="your-key"
```

Do not add the key or a `.env` file to Git.

## Run the complete evaluation

```bash
python project_starter.py
```

The command resets the SQLite database with seed 137, processes every row in `quote_requests_sample.csv`, prints customer-facing decisions, and rewrites `test_results.csv`.

## Verified results

| Measure | Result |
|---|---:|
| Requests evaluated | 20 |
| Fulfilled requests | 9 |
| Requests with a cash-balance change | 9 |
| Rejected requests with reasons | 11 |
| Starting cash | $45,059.70 |
| Final cash | $46,093.24 |

The generated responses explain discounts, stock or supplier constraints, and delivery feasibility. They do not expose internal margins, credentials, stack traces, or database errors.

## Validation performed

The development checks covered database initialization, request parsing, ambiguous quantities, volume-discount boundaries, Pydantic AI agent execution and tool registration, historical-price benchmarking, rejection without mutation, successful inventory and cash updates, and the full-dataset rubric thresholds.

Verified commands:

```bash
python -m pytest -q ../dev_tests/test_beavers_choice.py
python -m compileall -q project_starter.py
python -m pip check
python project_starter.py
```

The development tests are intentionally outside this submission directory so the submitted project contains only one Python source file, as required by the assignment.

## Design safeguards

- Unsupported items and unknown package conversions are rejected instead of guessed.
- Every line is validated before any transaction is written.
- A multi-line request is not partially fulfilled.
- Replenishment must arrive by the requested deadline and fit within available cash.
- Rejected requests leave both cash and inventory unchanged.
