"""ADK agents for the categorize-and-report stage of the pipeline.

Parsing (tools.py / parser.py) happens as a plain Python function call
before these agents ever run, not as a third agent in the chain. There
is exactly one correct way to parse a given file, no reasoning or tool
selection is involved, so giving a model the chance to decide whether
or how to call the parser would reintroduce the exact risk section 2.3
was built to remove. These two agents handle the parts that actually
are reasoning tasks: categorizing transactions and summarizing them.
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
        "The parsed transactions are in state['parsed_statement']['transactions']. "
        "For each transaction, assign a short category (e.g. Groceries, "
        "Dining, Transfer, Income, Utilities, Subscription, Other). "
        "Return the full list of transactions with a 'category' field "
        "added to each one, as JSON, and nothing else."
    ),
    output_key="categorized_transactions",
)

reporter_agent = Agent(
    model=MODEL_NAME,
    name="reporter_agent",
    description="Writes a short natural-language summary of categorized spending.",
    instruction=(
        "The categorized transactions are in state['categorized_transactions']. "
        "Write a short summary (3-5 sentences) of spending by category. "
        "If state['parsed_statement']['warning'] is non-empty, mention "
        "that warning explicitly at the end of your summary so the "
        "reader knows the parse may be incomplete."
    ),
    output_key="final_report",
)
