import pandas as pd
import numpy as np
import asyncio
import json
import os
import re
import time
import dotenv
import ast
from sqlalchemy.sql import text
from datetime import datetime, timedelta
from typing import Dict, List, Union
from sqlalchemy import create_engine, Engine
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

# Create an SQLite database
db_engine = create_engine("sqlite:///munder_difflin.db")

# List containing the different kinds of papers
paper_supplies = [
    # Paper Types (priced per sheet unless specified)
    {"item_name": "A4 paper",                         "category": "paper",        "unit_price": 0.05},
    {"item_name": "Letter-sized paper",              "category": "paper",        "unit_price": 0.06},
    {"item_name": "Cardstock",                        "category": "paper",        "unit_price": 0.15},
    {"item_name": "Colored paper",                    "category": "paper",        "unit_price": 0.10},
    {"item_name": "Glossy paper",                     "category": "paper",        "unit_price": 0.20},
    {"item_name": "Matte paper",                      "category": "paper",        "unit_price": 0.18},
    {"item_name": "Recycled paper",                   "category": "paper",        "unit_price": 0.08},
    {"item_name": "Eco-friendly paper",               "category": "paper",        "unit_price": 0.12},
    {"item_name": "Poster paper",                     "category": "paper",        "unit_price": 0.25},
    {"item_name": "Banner paper",                     "category": "paper",        "unit_price": 0.30},
    {"item_name": "Kraft paper",                      "category": "paper",        "unit_price": 0.10},
    {"item_name": "Construction paper",               "category": "paper",        "unit_price": 0.07},
    {"item_name": "Wrapping paper",                   "category": "paper",        "unit_price": 0.15},
    {"item_name": "Glitter paper",                    "category": "paper",        "unit_price": 0.22},
    {"item_name": "Decorative paper",                 "category": "paper",        "unit_price": 0.18},
    {"item_name": "Letterhead paper",                 "category": "paper",        "unit_price": 0.12},
    {"item_name": "Legal-size paper",                 "category": "paper",        "unit_price": 0.08},
    {"item_name": "Crepe paper",                      "category": "paper",        "unit_price": 0.05},
    {"item_name": "Photo paper",                      "category": "paper",        "unit_price": 0.25},
    {"item_name": "Uncoated paper",                   "category": "paper",        "unit_price": 0.06},
    {"item_name": "Butcher paper",                    "category": "paper",        "unit_price": 0.10},
    {"item_name": "Heavyweight paper",                "category": "paper",        "unit_price": 0.20},
    {"item_name": "Standard copy paper",              "category": "paper",        "unit_price": 0.04},
    {"item_name": "Bright-colored paper",             "category": "paper",        "unit_price": 0.12},
    {"item_name": "Patterned paper",                  "category": "paper",        "unit_price": 0.15},

    # Product Types (priced per unit)
    {"item_name": "Paper plates",                     "category": "product",      "unit_price": 0.10},  # per plate
    {"item_name": "Paper cups",                       "category": "product",      "unit_price": 0.08},  # per cup
    {"item_name": "Paper napkins",                    "category": "product",      "unit_price": 0.02},  # per napkin
    {"item_name": "Disposable cups",                  "category": "product",      "unit_price": 0.10},  # per cup
    {"item_name": "Table covers",                     "category": "product",      "unit_price": 1.50},  # per cover
    {"item_name": "Envelopes",                        "category": "product",      "unit_price": 0.05},  # per envelope
    {"item_name": "Sticky notes",                     "category": "product",      "unit_price": 0.03},  # per sheet
    {"item_name": "Notepads",                         "category": "product",      "unit_price": 2.00},  # per pad
    {"item_name": "Invitation cards",                 "category": "product",      "unit_price": 0.50},  # per card
    {"item_name": "Flyers",                           "category": "product",      "unit_price": 0.15},  # per flyer
    {"item_name": "Party streamers",                  "category": "product",      "unit_price": 0.05},  # per roll
    {"item_name": "Decorative adhesive tape (washi tape)", "category": "product", "unit_price": 0.20},  # per roll
    {"item_name": "Paper party bags",                 "category": "product",      "unit_price": 0.25},  # per bag
    {"item_name": "Name tags with lanyards",          "category": "product",      "unit_price": 0.75},  # per tag
    {"item_name": "Presentation folders",             "category": "product",      "unit_price": 0.50},  # per folder

    # Large-format items (priced per unit)
    {"item_name": "Large poster paper (24x36 inches)", "category": "large_format", "unit_price": 1.00},
    {"item_name": "Rolls of banner paper (36-inch width)", "category": "large_format", "unit_price": 2.50},

    # Specialty papers
    {"item_name": "100 lb cover stock",               "category": "specialty",    "unit_price": 0.50},
    {"item_name": "80 lb text paper",                 "category": "specialty",    "unit_price": 0.40},
    {"item_name": "250 gsm cardstock",                "category": "specialty",    "unit_price": 0.30},
    {"item_name": "220 gsm poster paper",             "category": "specialty",    "unit_price": 0.35},
]


class OrderLine(BaseModel):
    """One normalized catalog line extracted from a customer request."""

    item_name: str
    quantity: int = Field(gt=0)


class ParsedRequest(BaseModel):
    """Deterministic representation of the items and delivery constraint."""

    lines: List[OrderLine] = Field(default_factory=list)
    deadline: str
    rejection_reason: str | None = None


class OrderDecision(BaseModel):
    """Final customer-visible outcome and evaluation metadata."""

    fulfilled: bool
    total_amount: float = 0.0
    reason: str
    response: str


ITEM_ALIASES = (
    ("washi tape", "Decorative adhesive tape (washi tape)"),
    ("poster board", "Large poster paper (24x36 inches)"),
    ("paper napkin", "Paper napkins"),
    ("table napkin", "Paper napkins"),
    ("paper cup", "Paper cups"),
    ("paper plate", "Paper plates"),
    ("streamer", "Party streamers"),
    ("glossy", "Glossy paper"),
    ("matte", "Matte paper"),
    ("cardstock", "Cardstock"),
    ("colored paper", "Colored paper"),
    ("colour paper", "Colored paper"),
    ("construction paper", "Construction paper"),
    ("recycled paper", "Recycled paper"),
    ("kraft paper", "Kraft paper"),
    ("poster paper", "Poster paper"),
    ("a4 paper", "A4 paper"),
    ("a4 printer paper", "A4 paper"),
    ("a4 printing paper", "A4 paper"),
    ("standard printer paper", "Standard copy paper"),
    ("standard printing paper", "Standard copy paper"),
    ("white printer paper", "Standard copy paper"),
    ("printing paper", "Standard copy paper"),
    ("printer paper", "Standard copy paper"),
    ("flyer", "Flyers"),
)


def _normalize_item_description(description: str) -> str | None:
    """Map common request wording to one item in the supplied catalog."""

    normalized = re.sub(r"[^a-z0-9]+", " ", description.lower()).strip()
    for alias, item_name in ITEM_ALIASES:
        if alias in normalized:
            return item_name
    return None


def _clean_unsupported_description(description: str) -> str:
    """Keep the product phrase while removing trailing request boilerplate."""

    product_phrase = re.split(
        r"(?:[.!?]\s*|,\s*)(?=(?:please|we|i)\b)",
        description,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    return product_phrase.strip(" .;,-\t") or "unspecified product"


def parse_customer_request(request_text: str, request_date: str) -> ParsedRequest:
    """Extract catalog lines and an explicit deadline without inventing missing data."""

    ambiguous_quantities = bool(
        re.search(r"\b\d[\d,]*\s+\d[\d,]+(?:\s+\d[\d,]*)?\s+(?:sheets?|reams?|rolls?)\b", request_text)
    )
    deadline = request_date
    deadline_match = re.search(
        r"\bby\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})", request_text, re.IGNORECASE
    )
    if deadline_match:
        deadline = datetime.strptime(deadline_match.group(1), "%B %d, %Y").strftime("%Y-%m-%d")
    item_text = request_text[: deadline_match.start()] if deadline_match else request_text

    line_pattern = re.compile(
        r"(?<![\d,])(?P<quantity>\d[\d,]*)\s+"
        r"(?P<unit>sheets?|reams?|rolls?|packets?|boxes?|units?)?\s*"
        r"(?:of\s+)?(?P<description>.*?)"
        r"(?=,\s*(?:[-•]\s*)?(?:(?:and|along with)\s+)?\d|"
        r"\s+(?:and|along with)\s+\d|\s+by\s+[A-Za-z]+\s+\d|$)",
        re.IGNORECASE,
    )

    lines = []
    unsupported = []
    normalized_item_text = re.sub(r"\s*[\r\n]+\s*[-•]?\s*", ", ", item_text)
    for match in line_pattern.finditer(normalized_item_text):
        quantity = int(match.group("quantity").replace(",", ""))
        unit = (match.group("unit") or "units").lower()
        description = match.group("description").strip(" .;-\t")
        item_name = _normalize_item_description(description)
        if item_name is None:
            unsupported.append(_clean_unsupported_description(description))
            continue
        if unit.startswith("ream"):
            quantity *= 500
        elif unit.startswith(("packet", "box")):
            product_phrase = _clean_unsupported_description(description)
            unsupported.append(f"{product_phrase} uses an unspecified package size")
            continue
        lines.append(OrderLine(item_name=item_name, quantity=quantity))

    rejection_reason = None
    if ambiguous_quantities:
        rejection_reason = "Ambiguous quantities are not assigned to specific products."
    elif unsupported:
        rejection_reason = "Unsupported or ambiguous item(s): " + ", ".join(unsupported)
    elif not lines:
        rejection_reason = "No unambiguous catalog items and quantities were found."

    return ParsedRequest(lines=lines, deadline=deadline, rejection_reason=rejection_reason)


def calculate_volume_discount(total_units: int) -> float:
    """Return a transparent quantity discount for the complete request."""

    if total_units >= 5000:
        return 0.15
    if total_units >= 2000:
        return 0.10
    if total_units >= 500:
        return 0.05
    return 0.0


def _historical_unit_price(historical_quotes: List[Dict]) -> float | None:
    """Return a median per-unit benchmark from usable historical quotes."""

    unit_prices = []
    for quote in historical_quotes:
        total_amount = float(quote.get("total_amount") or 0)
        if total_amount <= 0:
            continue
        request_text = str(quote.get("original_request") or "")
        request_date = str(quote.get("order_date") or "2025-01-01")[:10]
        parsed = parse_customer_request(request_text, request_date)
        total_units = sum(line.quantity for line in parsed.lines)
        if total_units:
            unit_price = total_amount / total_units
            if 0.01 <= unit_price <= 5.0:
                unit_prices.append(unit_price)
    if not unit_prices:
        return None
    return float(np.median(unit_prices))


def process_customer_request(request_text: str, request_date: str) -> OrderDecision:
    """Run one complete customer request through the orchestrator agent."""

    decision = _run_agent_tool(
        orchestrator_agent,
        "orchestrate_customer_request",
        request_text=request_text,
        request_date=request_date,
    )
    return OrderDecision.model_validate(decision)

# Given below are some utility functions you can use to implement your multi-agent system

def generate_sample_inventory(paper_supplies: list, coverage: float = 0.4, seed: int = 137) -> pd.DataFrame:
    """
    Generate inventory for exactly a specified percentage of items from the full paper supply list.

    This function randomly selects exactly `coverage` × N items from the `paper_supplies` list,
    and assigns each selected item:
    - a random stock quantity between 200 and 800,
    - a minimum stock level between 50 and 150.

    The random seed ensures reproducibility of selection and stock levels.

    Args:
        paper_supplies (list): A list of dictionaries, each representing a paper item with
                               keys 'item_name', 'category', and 'unit_price'.
        coverage (float, optional): Fraction of items to include in the inventory (default is 0.4, or 40%).
        seed (int, optional): Random seed for reproducibility (default is 137).

    Returns:
        pd.DataFrame: A DataFrame with the selected items and assigned inventory values, including:
                      - item_name
                      - category
                      - unit_price
                      - current_stock
                      - min_stock_level
    """
    # Ensure reproducible random output
    np.random.seed(seed)

    # Calculate number of items to include based on coverage
    num_items = int(len(paper_supplies) * coverage)

    # Randomly select item indices without replacement
    selected_indices = np.random.choice(
        range(len(paper_supplies)),
        size=num_items,
        replace=False
    )

    # Extract selected items from paper_supplies list
    selected_items = [paper_supplies[i] for i in selected_indices]

    # Construct inventory records
    inventory = []
    for item in selected_items:
        inventory.append({
            "item_name": item["item_name"],
            "category": item["category"],
            "unit_price": item["unit_price"],
            "current_stock": np.random.randint(200, 800),  # Realistic stock range
            "min_stock_level": np.random.randint(50, 150)  # Reasonable threshold for reordering
        })

    # Return inventory as a pandas DataFrame
    return pd.DataFrame(inventory)

def init_database(db_engine: Engine, seed: int = 137) -> Engine:
    """
    Set up the Munder Difflin database with all required tables and initial records.

    This function performs the following tasks:
    - Creates the 'transactions' table for logging stock orders and sales
    - Loads customer inquiries from 'quote_requests.csv' into a 'quote_requests' table
    - Loads previous quotes from 'quotes.csv' into a 'quotes' table, extracting useful metadata
    - Generates a random subset of paper inventory using `generate_sample_inventory`
    - Inserts initial financial records including available cash and starting stock levels

    Args:
        db_engine (Engine): A SQLAlchemy engine connected to the SQLite database.
        seed (int, optional): A random seed used to control reproducibility of inventory stock levels.
                              Default is 137.

    Returns:
        Engine: The same SQLAlchemy engine, after initializing all necessary tables and records.

    Raises:
        Exception: If an error occurs during setup, the exception is printed and raised.
    """
    try:
        # ----------------------------
        # 1. Create an empty 'transactions' table schema
        # ----------------------------
        transactions_schema = pd.DataFrame({
            "id": [],
            "item_name": [],
            "transaction_type": [],  # 'stock_orders' or 'sales'
            "units": [],             # Quantity involved
            "price": [],             # Total price for the transaction
            "transaction_date": [],  # ISO-formatted date
        })
        transactions_schema.to_sql("transactions", db_engine, if_exists="replace", index=False)

        # Set a consistent starting date
        initial_date = datetime(2025, 1, 1).isoformat()

        # ----------------------------
        # 2. Load and initialize 'quote_requests' table
        # ----------------------------
        quote_requests_df = pd.read_csv("quote_requests.csv")
        quote_requests_df["id"] = range(1, len(quote_requests_df) + 1)
        quote_requests_df.to_sql("quote_requests", db_engine, if_exists="replace", index=False)

        # ----------------------------
        # 3. Load and transform 'quotes' table
        # ----------------------------
        quotes_df = pd.read_csv("quotes.csv")
        quotes_df["request_id"] = range(1, len(quotes_df) + 1)
        quotes_df["order_date"] = initial_date

        # Unpack metadata fields (job_type, order_size, event_type) if present
        if "request_metadata" in quotes_df.columns:
            quotes_df["request_metadata"] = quotes_df["request_metadata"].apply(
                lambda x: ast.literal_eval(x) if isinstance(x, str) else x
            )
            quotes_df["job_type"] = quotes_df["request_metadata"].apply(lambda x: x.get("job_type", ""))
            quotes_df["order_size"] = quotes_df["request_metadata"].apply(lambda x: x.get("order_size", ""))
            quotes_df["event_type"] = quotes_df["request_metadata"].apply(lambda x: x.get("event_type", ""))

        # Retain only relevant columns
        quotes_df = quotes_df[[
            "request_id",
            "total_amount",
            "quote_explanation",
            "order_date",
            "job_type",
            "order_size",
            "event_type"
        ]]
        quotes_df.to_sql("quotes", db_engine, if_exists="replace", index=False)

        # ----------------------------
        # 4. Generate inventory and seed stock
        # ----------------------------
        inventory_df = generate_sample_inventory(paper_supplies, seed=seed)

        # Seed initial transactions
        initial_transactions = []

        # Add a starting cash balance via a dummy sales transaction
        initial_transactions.append({
            "item_name": None,
            "transaction_type": "sales",
            "units": None,
            "price": 50000.0,
            "transaction_date": initial_date,
        })

        # Add one stock order transaction per inventory item
        for _, item in inventory_df.iterrows():
            initial_transactions.append({
                "item_name": item["item_name"],
                "transaction_type": "stock_orders",
                "units": item["current_stock"],
                "price": item["current_stock"] * item["unit_price"],
                "transaction_date": initial_date,
            })

        # Commit transactions to database
        pd.DataFrame(initial_transactions).to_sql("transactions", db_engine, if_exists="append", index=False)

        # Save the inventory reference table
        inventory_df.to_sql("inventory", db_engine, if_exists="replace", index=False)

        return db_engine

    except Exception as e:
        print(f"Error initializing database: {e}")
        raise

def create_transaction(
    item_name: str,
    transaction_type: str,
    quantity: int,
    price: float,
    date: Union[str, datetime],
) -> int:
    """
    This function records a transaction of type 'stock_orders' or 'sales' with a specified
    item name, quantity, total price, and transaction date into the 'transactions' table of the database.

    Args:
        item_name (str): The name of the item involved in the transaction.
        transaction_type (str): Either 'stock_orders' or 'sales'.
        quantity (int): Number of units involved in the transaction.
        price (float): Total price of the transaction.
        date (str or datetime): Date of the transaction in ISO 8601 format.

    Returns:
        int: The ID of the newly inserted transaction.

    Raises:
        ValueError: If `transaction_type` is not 'stock_orders' or 'sales'.
        Exception: For other database or execution errors.
    """
    try:
        # Convert datetime to ISO string if necessary
        date_str = date.isoformat() if isinstance(date, datetime) else date

        # Validate transaction type
        if transaction_type not in {"stock_orders", "sales"}:
            raise ValueError("Transaction type must be 'stock_orders' or 'sales'")

        # Prepare transaction record as a single-row DataFrame
        transaction = pd.DataFrame([{
            "item_name": item_name,
            "transaction_type": transaction_type,
            "units": quantity,
            "price": price,
            "transaction_date": date_str,
        }])

        # Insert the record into the database
        transaction.to_sql("transactions", db_engine, if_exists="append", index=False)

        # Fetch and return the ID of the inserted row
        result = pd.read_sql("SELECT last_insert_rowid() as id", db_engine)
        return int(result.iloc[0]["id"])

    except Exception as e:
        print(f"Error creating transaction: {e}")
        raise

def get_all_inventory(as_of_date: str) -> Dict[str, int]:
    """
    Retrieve a snapshot of available inventory as of a specific date.

    This function calculates the net quantity of each item by summing
    all stock orders and subtracting all sales up to and including the given date.

    Only items with positive stock are included in the result.

    Args:
        as_of_date (str): ISO-formatted date string (YYYY-MM-DD) representing the inventory cutoff.

    Returns:
        Dict[str, int]: A dictionary mapping item names to their current stock levels.
    """
    # SQL query to compute stock levels per item as of the given date
    query = """
        SELECT
            item_name,
            SUM(CASE
                WHEN transaction_type = 'stock_orders' THEN units
                WHEN transaction_type = 'sales' THEN -units
                ELSE 0
            END) as stock
        FROM transactions
        WHERE item_name IS NOT NULL
        AND transaction_date <= :as_of_date
        GROUP BY item_name
        HAVING stock > 0
    """

    # Execute the query with the date parameter
    result = pd.read_sql(query, db_engine, params={"as_of_date": as_of_date})

    # Convert the result into a dictionary {item_name: stock}
    return dict(zip(result["item_name"], result["stock"]))

def get_stock_level(item_name: str, as_of_date: Union[str, datetime]) -> pd.DataFrame:
    """
    Retrieve the stock level of a specific item as of a given date.

    This function calculates the net stock by summing all 'stock_orders' and
    subtracting all 'sales' transactions for the specified item up to the given date.

    Args:
        item_name (str): The name of the item to look up.
        as_of_date (str or datetime): The cutoff date (inclusive) for calculating stock.

    Returns:
        pd.DataFrame: A single-row DataFrame with columns 'item_name' and 'current_stock'.
    """
    # Convert date to ISO string format if it's a datetime object
    if isinstance(as_of_date, datetime):
        as_of_date = as_of_date.isoformat()

    # SQL query to compute net stock level for the item
    stock_query = """
        SELECT
            item_name,
            COALESCE(SUM(CASE
                WHEN transaction_type = 'stock_orders' THEN units
                WHEN transaction_type = 'sales' THEN -units
                ELSE 0
            END), 0) AS current_stock
        FROM transactions
        WHERE item_name = :item_name
        AND transaction_date <= :as_of_date
    """

    # Execute query and return result as a DataFrame
    return pd.read_sql(
        stock_query,
        db_engine,
        params={"item_name": item_name, "as_of_date": as_of_date},
    )

def get_supplier_delivery_date(input_date_str: str, quantity: int) -> str:
    """
    Estimate the supplier delivery date based on the requested order quantity and a starting date.

    Delivery lead time increases with order size:
        - ≤10 units: same day
        - 11–100 units: 1 day
        - 101–1000 units: 4 days
        - >1000 units: 7 days

    Args:
        input_date_str (str): The starting date in ISO format (YYYY-MM-DD).
        quantity (int): The number of units in the order.

    Returns:
        str: Estimated delivery date in ISO format (YYYY-MM-DD).
    """
    # Attempt to parse the input date
    try:
        input_date_dt = datetime.fromisoformat(input_date_str.split("T")[0])
    except (ValueError, TypeError):
        # Fallback to current date on format error
        input_date_dt = datetime.now()

    # Determine delivery delay based on quantity
    if quantity <= 10:
        days = 0
    elif quantity <= 100:
        days = 1
    elif quantity <= 1000:
        days = 4
    else:
        days = 7

    # Add delivery days to the starting date
    delivery_date_dt = input_date_dt + timedelta(days=days)

    # Return formatted delivery date
    return delivery_date_dt.strftime("%Y-%m-%d")

def get_cash_balance(as_of_date: Union[str, datetime]) -> float:
    """
    Calculate the current cash balance as of a specified date.

    The balance is computed by subtracting total stock purchase costs ('stock_orders')
    from total revenue ('sales') recorded in the transactions table up to the given date.

    Args:
        as_of_date (str or datetime): The cutoff date (inclusive) in ISO format or as a datetime object.

    Returns:
        float: Net cash balance as of the given date. Returns 0.0 if no transactions exist or an error occurs.
    """
    try:
        # Convert date to ISO format if it's a datetime object
        if isinstance(as_of_date, datetime):
            as_of_date = as_of_date.isoformat()

        # Query all transactions on or before the specified date
        transactions = pd.read_sql(
            "SELECT * FROM transactions WHERE transaction_date <= :as_of_date",
            db_engine,
            params={"as_of_date": as_of_date},
        )

        # Compute the difference between sales and stock purchases
        if not transactions.empty:
            total_sales = transactions.loc[transactions["transaction_type"] == "sales", "price"].sum()
            total_purchases = transactions.loc[transactions["transaction_type"] == "stock_orders", "price"].sum()
            return float(total_sales - total_purchases)

        return 0.0

    except Exception as e:
        print(f"Error getting cash balance: {e}")
        return 0.0


def generate_financial_report(as_of_date: Union[str, datetime]) -> Dict:
    """
    Generate a complete financial report for the company as of a specific date.

    This includes:
    - Cash balance
    - Inventory valuation
    - Combined asset total
    - Itemized inventory breakdown
    - Top 5 best-selling products

    Args:
        as_of_date (str or datetime): The date (inclusive) for which to generate the report.

    Returns:
        Dict: A dictionary containing the financial report fields:
            - 'as_of_date': The date of the report
            - 'cash_balance': Total cash available
            - 'inventory_value': Total value of inventory
            - 'total_assets': Combined cash and inventory value
            - 'inventory_summary': List of items with stock and valuation details
            - 'top_selling_products': List of top 5 products by revenue
    """
    # Normalize date input
    if isinstance(as_of_date, datetime):
        as_of_date = as_of_date.isoformat()

    # Get current cash balance
    cash = get_cash_balance(as_of_date)

    # Get current inventory snapshot
    inventory_df = pd.read_sql("SELECT * FROM inventory", db_engine)
    inventory_value = 0.0
    inventory_summary = []

    # Compute total inventory value and summary by item
    for _, item in inventory_df.iterrows():
        stock_info = get_stock_level(item["item_name"], as_of_date)
        stock = stock_info["current_stock"].iloc[0]
        item_value = stock * item["unit_price"]
        inventory_value += item_value

        inventory_summary.append({
            "item_name": item["item_name"],
            "stock": stock,
            "unit_price": item["unit_price"],
            "value": item_value,
        })

    # Identify top-selling products by revenue
    top_sales_query = """
        SELECT item_name, SUM(units) as total_units, SUM(price) as total_revenue
        FROM transactions
        WHERE transaction_type = 'sales' AND transaction_date <= :date
        GROUP BY item_name
        ORDER BY total_revenue DESC
        LIMIT 5
    """
    top_sales = pd.read_sql(top_sales_query, db_engine, params={"date": as_of_date})
    top_selling_products = top_sales.to_dict(orient="records")

    return {
        "as_of_date": as_of_date,
        "cash_balance": cash,
        "inventory_value": inventory_value,
        "total_assets": cash + inventory_value,
        "inventory_summary": inventory_summary,
        "top_selling_products": top_selling_products,
    }


def search_quote_history(search_terms: List[str], limit: int = 5) -> List[Dict]:
    """
    Retrieve a list of historical quotes that match any of the provided search terms.

    The function searches both the original customer request (from `quote_requests`) and
    the explanation for the quote (from `quotes`) for each keyword. Results are sorted by
    most recent order date and limited by the `limit` parameter.

    Args:
        search_terms (List[str]): List of terms to match against customer requests and explanations.
        limit (int, optional): Maximum number of quote records to return. Default is 5.

    Returns:
        List[Dict]: A list of matching quotes, each represented as a dictionary with fields:
            - original_request
            - total_amount
            - quote_explanation
            - job_type
            - order_size
            - event_type
            - order_date
    """
    conditions = []
    params = {}

    # Build SQL WHERE clause using LIKE filters for each search term
    for i, term in enumerate(search_terms):
        param_name = f"term_{i}"
        conditions.append(
            f"(LOWER(qr.response) LIKE :{param_name} OR "
            f"LOWER(q.quote_explanation) LIKE :{param_name})"
        )
        params[param_name] = f"%{term.lower()}%"

    # Combine conditions; fallback to always-true if no terms provided
    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Final SQL query to join quotes with quote_requests
    query = f"""
        SELECT
            qr.response AS original_request,
            q.total_amount,
            q.quote_explanation,
            q.job_type,
            q.order_size,
            q.event_type,
            q.order_date
        FROM quotes q
        JOIN quote_requests qr ON q.request_id = qr.id
        WHERE {where_clause}
        ORDER BY q.order_date DESC
        LIMIT {limit}
    """

    # Execute parameterized query
    with db_engine.connect() as conn:
        result = conn.execute(text(query), params)
        return [dict(row._mapping) for row in result]

########################
########################
########################
# YOUR MULTI AGENT STARTS HERE
########################
########################
########################


def _deterministic_tool_router(messages: list, info: AgentInfo) -> ModelResponse:
    """Drive one explicit tool call through Pydantic AI without a network dependency."""

    for message in reversed(messages):
        for part in message.parts:
            if isinstance(part, ToolReturnPart):
                return ModelResponse(
                    parts=[TextPart(json.dumps(part.content, default=str))]
                )

    for message in reversed(messages):
        for part in message.parts:
            if not isinstance(part, UserPromptPart) or not isinstance(part.content, str):
                continue
            request = json.loads(part.content)
            tool_name = request["tool_name"]
            available_tools = {tool.name for tool in info.function_tools}
            if tool_name not in available_tools:
                raise ValueError(f"Agent does not own requested tool: {tool_name}")
            return ModelResponse(
                parts=[ToolCallPart(tool_name, request.get("args", {}))]
            )
    raise ValueError("The agent request did not contain a tool-routing instruction.")


def _build_agent_model():
    """Use Udacity's endpoint when configured and a deterministic model otherwise."""

    dotenv.load_dotenv()
    api_key = os.getenv("UDACITY_OPENAI_API_KEY")
    if not api_key:
        return FunctionModel(_deterministic_tool_router)
    return OpenAIChatModel(
        os.getenv("UDACITY_OPENAI_MODEL", "gpt-4o-mini"),
        provider=OpenAIProvider(
            base_url="https://openai.vocareum.com/v1",
            api_key=api_key,
        ),
    )


def _run_agent_tool(agent: Agent, tool_name: str, **arguments):
    """Execute an owned tool through an agent and decode its JSON result."""

    prompt = json.dumps({"tool_name": tool_name, "args": arguments})
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    result = agent.run_sync(prompt)
    if isinstance(result.output, str):
        return json.loads(result.output)
    return result.output


async def _run_agent_tool_async(agent: Agent, tool_name: str, **arguments):
    """Execute an owned tool from inside another running agent."""

    prompt = json.dumps({"tool_name": tool_name, "args": arguments})
    result = await agent.run(prompt)
    if isinstance(result.output, str):
        return json.loads(result.output)
    return result.output


agent_model = _build_agent_model()

orchestrator_agent = Agent(
    agent_model,
    name="orchestrator_agent",
    instructions=(
        "Coordinate inventory, quoting, and sales responsibilities. Return concise, "
        "customer-safe text and never expose internal errors, margins, or database details."
    ),
)
inventory_agent = Agent(
    agent_model,
    name="inventory_agent",
    instructions=(
        "Report stock accurately, assess shortages, and use supplier timing before "
        "recommending replenishment. Do not quote prices or record sales."
    ),
)
quote_agent = Agent(
    agent_model,
    name="quote_agent",
    instructions=(
        "Use historical quote context and the documented volume tiers to prepare an "
        "explainable customer price. Do not mutate inventory or cash."
    ),
)
sales_agent = Agent(
    agent_model,
    name="sales_agent",
    instructions=(
        "Record approved stock purchases and sales only after the orchestrator has "
        "validated every line and the delivery deadline."
    ),
)


@inventory_agent.tool_plain
def inventory_snapshot_tool(as_of_date: str) -> Dict[str, int]:
    """List every positive inventory balance using get_all_inventory."""

    return get_all_inventory(as_of_date)


@inventory_agent.tool_plain
def stock_level_tool(item_name: str, as_of_date: str) -> int:
    """Return available units for one catalog item using get_stock_level."""

    stock = get_stock_level(item_name, as_of_date)
    return int(stock["current_stock"].iloc[0])


@inventory_agent.tool_plain
def supplier_delivery_tool(request_date: str, quantity: int) -> str:
    """Estimate replenishment arrival using get_supplier_delivery_date."""

    return get_supplier_delivery_date(request_date, quantity)


@quote_agent.tool_plain
def quote_history_tool(search_terms: List[str], limit: int = 5) -> List[Dict]:
    """Find comparable historical quotes using search_quote_history."""

    return search_quote_history(search_terms, limit)


@sales_agent.tool_plain
def record_transaction_tool(
    item_name: str,
    transaction_type: str,
    quantity: int,
    price: float,
    transaction_date: str,
) -> int:
    """Record an approved purchase or sale using create_transaction."""

    return create_transaction(item_name, transaction_type, quantity, price, transaction_date)


@sales_agent.tool_plain
def cash_balance_tool(as_of_date: str) -> float:
    """Return available company cash using get_cash_balance."""

    return get_cash_balance(as_of_date)


@orchestrator_agent.tool_plain
def financial_report_tool(as_of_date: str) -> Dict:
    """Return the complete operating snapshot using generate_financial_report."""

    return generate_financial_report(as_of_date)


@orchestrator_agent.tool_plain
async def delegate_inventory_review(
    lines: List[Dict], request_date: str, deadline: str
) -> Dict:
    """Delegate stock and supplier checks to the inventory agent's tools."""

    catalog = {item["item_name"]: item for item in paper_supplies}
    shortages = []
    latest_supplier_date = request_date
    reorder_cost = 0.0
    for line in lines:
        item_name = line["item_name"]
        quantity = int(line["quantity"])
        available = await _run_agent_tool_async(
            inventory_agent,
            "stock_level_tool",
            item_name=item_name,
            as_of_date=request_date,
        )
        shortage = max(quantity - available, 0)
        if not shortage:
            continue
        supplier_date = await _run_agent_tool_async(
            inventory_agent,
            "supplier_delivery_tool",
            request_date=request_date,
            quantity=shortage,
        )
        if supplier_date > deadline:
            return {
                "feasible": False,
                "reason": (
                    f"{item_name} cannot arrive by {deadline}; "
                    f"the earliest replenishment date is {supplier_date}."
                ),
                "shortages": [],
            }
        unit_cost = float(catalog[item_name]["unit_price"])
        reorder_cost += shortage * unit_cost
        latest_supplier_date = max(latest_supplier_date, supplier_date)
        shortages.append(
            {"item_name": item_name, "quantity": shortage, "unit_cost": unit_cost}
        )
    return {
        "feasible": True,
        "reason": "Every line is available or can be replenished before the deadline.",
        "shortages": shortages,
        "latest_supplier_date": latest_supplier_date,
        "reorder_cost": round(reorder_cost, 2),
    }


@orchestrator_agent.tool_plain
async def delegate_quote_preparation(lines: List[Dict]) -> Dict:
    """Delegate historical context and pricing to the quote agent's tools."""

    catalog = {item["item_name"]: item for item in paper_supplies}
    search_terms = [lines[0]["item_name"].split()[0]]
    historical_quotes = await _run_agent_tool_async(
        quote_agent,
        "quote_history_tool",
        search_terms=search_terms,
        limit=3,
    )
    total_units = sum(int(line["quantity"]) for line in lines)
    discount = calculate_volume_discount(total_units)
    base_cost = sum(
        int(line["quantity"]) * float(catalog[line["item_name"]]["unit_price"])
        for line in lines
    )
    catalog_unit_cost = base_cost / total_units
    standard_unit_price = catalog_unit_cost * 1.35
    historical_unit_price = _historical_unit_price(historical_quotes)
    pricing_multiplier = 1.35
    pricing_basis = "The quote was checked against relevant prior requests."
    if historical_unit_price is not None:
        if historical_unit_price < standard_unit_price * 0.50:
            pricing_multiplier = 1.25
            pricing_basis = (
                "Historical prices supported a more competitive customer rate."
            )
        elif historical_unit_price > standard_unit_price * 2.00:
            pricing_multiplier = 1.45
            pricing_basis = (
                "Historical prices supported a modest market adjustment."
            )
    elif not historical_quotes:
        pricing_basis = "The quote follows the standard catalog pricing policy."

    total_amount = round(base_cost * pricing_multiplier * (1 - discount), 2)
    line_amounts = []
    allocated = 0.0
    for index, line in enumerate(lines):
        if index == len(lines) - 1:
            line_amount = round(total_amount - allocated, 2)
        else:
            line_amount = round(
                int(line["quantity"])
                * float(catalog[line["item_name"]]["unit_price"])
                * pricing_multiplier
                * (1 - discount),
                2,
            )
            allocated += line_amount
        line_amounts.append(line_amount)
    return {
        "total_amount": total_amount,
        "discount": discount,
        "historical_match_count": len(historical_quotes),
        "pricing_basis": pricing_basis,
        "line_amounts": line_amounts,
    }


@orchestrator_agent.tool_plain
async def delegate_sales_finalization(
    lines: List[Dict],
    shortages: List[Dict],
    line_amounts: List[float],
    request_date: str,
) -> Dict:
    """Delegate affordability checks and approved writes to the sales agent's tools."""

    reorder_cost = sum(
        int(shortage["quantity"]) * float(shortage["unit_cost"])
        for shortage in shortages
    )
    available_cash = await _run_agent_tool_async(
        sales_agent,
        "cash_balance_tool",
        as_of_date=request_date,
    )
    if reorder_cost > available_cash:
        return {
            "completed": False,
            "reason": "The required replenishment cannot be responsibly funded at this time.",
            "transaction_ids": [],
        }

    transaction_ids = []
    for shortage in shortages:
        transaction_ids.append(
            await _run_agent_tool_async(
                sales_agent,
                "record_transaction_tool",
                item_name=shortage["item_name"],
                transaction_type="stock_orders",
                quantity=int(shortage["quantity"]),
                price=round(
                    int(shortage["quantity"]) * float(shortage["unit_cost"]), 2
                ),
                transaction_date=request_date,
            )
        )
    for line, line_amount in zip(lines, line_amounts):
        transaction_ids.append(
            await _run_agent_tool_async(
                sales_agent,
                "record_transaction_tool",
                item_name=line["item_name"],
                transaction_type="sales",
                quantity=int(line["quantity"]),
                price=float(line_amount),
                transaction_date=request_date,
            )
        )
    return {
        "completed": True,
        "reason": "The replenishment and sale transactions were recorded.",
        "transaction_ids": transaction_ids,
    }


@orchestrator_agent.tool_plain
async def orchestrate_customer_request(
    request_text: str, request_date: str
) -> Dict:
    """Parse one request, delegate worker decisions, and compose the response."""

    parsed = parse_customer_request(request_text, request_date)
    if parsed.rejection_reason:
        reason = parsed.rejection_reason
        return OrderDecision(
            fulfilled=False,
            reason=reason,
            response=(
                f"We are unable to fulfill this request because {reason.lower()} "
                "No sale was recorded."
            ),
        ).model_dump()

    if parsed.deadline < request_date:
        reason = "The requested delivery date is earlier than the request date."
        return OrderDecision(
            fulfilled=False,
            reason=reason,
            response=(
                f"We are unable to fulfill this request because {reason.lower()} "
                "No sale was recorded."
            ),
        ).model_dump()

    lines = [line.model_dump() for line in parsed.lines]
    inventory_review = await delegate_inventory_review(
        lines, request_date, parsed.deadline
    )
    if not inventory_review["feasible"]:
        reason = inventory_review["reason"]
        return OrderDecision(
            fulfilled=False,
            reason=reason,
            response=(
                f"We are unable to fulfill this request because {reason} "
                "No sale was recorded."
            ),
        ).model_dump()

    quote_plan = await delegate_quote_preparation(lines)
    sales_receipt = await delegate_sales_finalization(
        lines,
        inventory_review["shortages"],
        quote_plan["line_amounts"],
        request_date,
    )
    if not sales_receipt["completed"]:
        reason = sales_receipt["reason"]
        return OrderDecision(
            fulfilled=False,
            reason=reason,
            response=(
                f"We are unable to fulfill this request because {reason.lower()} "
                "No sale was recorded."
            ),
        ).model_dump()

    item_summary = ", ".join(
        f"{line.quantity:,} {line.item_name}" for line in parsed.lines
    )
    discount_text = (
        f" A {quote_plan['discount']:.0%} volume discount is included."
        if quote_plan["discount"]
        else ""
    )
    replenishment_text = (
        f" Required replenishment is feasible by {inventory_review['latest_supplier_date']}."
        if inventory_review["shortages"]
        else " All requested items are available from current stock."
    )
    response = (
        f"Order confirmed for {item_summary}. Total: ${quote_plan['total_amount']:,.2f}."
        f"{discount_text}{replenishment_text} {quote_plan['pricing_basis']} "
        f"Delivery by {parsed.deadline} is feasible."
    )
    return OrderDecision(
        fulfilled=True,
        total_amount=quote_plan["total_amount"],
        reason="All requested lines passed inventory, supplier, and cash checks.",
        response=response,
    ).model_dump()


# Run your test scenarios by writing them here. Make sure to keep track of them.

def run_test_scenarios():
    """Evaluate every supplied request in date order and save rubric evidence."""

    print("Initializing Database...")
    init_database(db_engine)
    quote_requests_sample = pd.read_csv("quote_requests_sample.csv")
    quote_requests_sample["request_date"] = pd.to_datetime(
        quote_requests_sample["request_date"], format="%m/%d/%y", errors="coerce"
    )
    quote_requests_sample.dropna(subset=["request_date"], inplace=True)
    quote_requests_sample = quote_requests_sample.sort_values("request_date")

    initial_date = quote_requests_sample["request_date"].min().strftime("%Y-%m-%d")
    current_cash = get_cash_balance(initial_date)
    results = []

    for idx, row in quote_requests_sample.iterrows():
        request_date = row["request_date"].strftime("%Y-%m-%d")
        cash_before = current_cash
        decision = process_customer_request(row["request"], request_date)
        report = financial_report_tool(request_date)
        current_cash = float(report["cash_balance"])
        current_inventory = float(report["inventory_value"])
        cash_changed = abs(current_cash - cash_before) > 0.005

        print(f"\n=== Request {idx + 1} ===")
        print(f"Context: {row['job']} organizing {row['event']}")
        print(f"Response: {decision.response}")
        print(f"Updated Cash: ${current_cash:.2f}")
        print(f"Updated Inventory: ${current_inventory:.2f}")

        results.append(
            {
                "request_id": idx + 1,
                "request_date": request_date,
                "fulfilled": decision.fulfilled,
                "total_amount": decision.total_amount,
                "reason": decision.reason,
                "cash_before": cash_before,
                "cash_balance": current_cash,
                "cash_changed": cash_changed,
                "inventory_value": current_inventory,
                "response": decision.response,
            }
        )

    final_date = quote_requests_sample["request_date"].max().strftime("%Y-%m-%d")
    final_report = financial_report_tool(final_date)
    print("\n===== FINAL FINANCIAL REPORT =====")
    print(f"Final Cash: ${final_report['cash_balance']:.2f}")
    print(f"Final Inventory: ${final_report['inventory_value']:.2f}")

    pd.DataFrame(results).to_csv("test_results.csv", index=False)
    return results


if __name__ == "__main__":
    results = run_test_scenarios()
