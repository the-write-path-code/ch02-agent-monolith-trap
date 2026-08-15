"""ADK agents for the categorize-and-report stage of the pipeline.

Parsing (tools.py / parser.py) happens as a plain Python function call
before these agents ever run, not as a third agent in the chain. There
is exactly one correct way to parse a given file, no reasoning or tool
selection is involved, so giving a model the chance to decide whether
or how to call the parser would reintroduce the exact risk section 2.3
was built to remove. These two agents handle the parts that actually
are reasoning tasks: categorizing transactions and summarizing them.

Important: these agents read the transaction data from the conversation
history (the initial user message, built in pipeline.py), not from a
session-state key reference in the instruction text. An earlier version
of this file told the model the data was "in state['parsed_statement']",
which is just a string describing a location, it doesn't actually put
any data in front of the model. That produced a fully fabricated report
with numbers that didn't exist anywhere in the source document. Passing
the real JSON directly in the message is what makes the model's output
actually grounded in the parsed statement.
"""
import os

from dotenv import load_dotenv
from google.adk.agents import Agent

load_dotenv()

MODEL_NAME = os.environ.get("MODEL_NAME", "gemini-3.1-flash-lite")

categorizer_agent = Agent(
    model=MODEL_NAME,
    name="categorizer_agent",
    description="Assigns a spending category to each transaction.",
    instruction=(
        "The user's message contains a JSON object with a 'transactions' "
        "list, each item has 'date', 'description', and 'amount'. "
        "For each transaction, add a 'category' field (e.g. Groceries, "
        "Dining, Transfer, Income, Utilities, Subscription, Fees, Other) "
        "based on the description. Do not invent, drop, merge, or alter "
        "any date, description, or amount, only add the category field. "
        "Return ONLY the JSON list of transactions with categories added, "
        "no markdown fences, no commentary, no summary text."
    ),
    output_key="categorized_transactions",
)

reporter_agent = Agent(
    model=MODEL_NAME,
    name="reporter_agent",
    description="Writes a clean Markdown summary report of categorized spending.",
    instruction=(
        "The previous turn in this conversation contains a JSON list of "
        "categorized transactions, use that exact data, do not invent new "
        "transactions, amounts, or categories not present in it. "
        "Write a clean, well-formatted Markdown report with this structure:\n"
        "1. A '## Statement Summary' heading with the billing period if "
        "visible in the data, total number of transactions, and net total "
        "amount (sum of all amounts).\n"
        "2. A '## Spending by Category' heading with a Markdown table: "
        "columns Category, Transaction Count, Total Amount. Sort by "
        "total amount, largest first.\n"
        "3. A '## Transactions' heading with a Markdown table listing every "
        "transaction: Date, Description, Amount, Category.\n"
        "4. If a parsing warning was mentioned earlier in the conversation, "
        "add a '## Note' heading at the end quoting that warning verbatim, "
        "so the reader knows the source data may be incomplete. Omit this "
        "section entirely if no warning was mentioned.\n"
        "Return ONLY the Markdown report, no extra commentary before or "
        "after it."
    ),
    output_key="final_report",
)
