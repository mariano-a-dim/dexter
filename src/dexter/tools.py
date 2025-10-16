from langchain.tools import tool
from typing import List, Callable
import os
from datetime import datetime
from pydantic import BaseModel, Field
from tavily import TavilyClient

####################################
# Tools
####################################

class WebSearchInput(BaseModel):
    query: str = Field(description="The search query to look up on the internet. Be specific and include relevant keywords for better results.")
    max_results: int = Field(default=5, description="Maximum number of search results to return. Default is 5.")

class CalculatorInput(BaseModel):
    expression: str = Field(description="A mathematical expression to calculate. Examples: '435.15 - 349.07', '(100 / 50) * 2', '15.5 + 20.3'")

@tool(args_schema=WebSearchInput)
def search_web(query: str, max_results: int = 5) -> dict:
    """
    Searches the internet for information using Tavily API.
    Useful for finding recent news, articles, analysis, and general information about any topic.
    Returns a list of relevant web pages with titles, URLs, and content snippets.
    """
    try:
        tavily_api_key = os.getenv("TAVILY_API_KEY")
        if not tavily_api_key:
            return {"error": "TAVILY_API_KEY not found in environment variables"}
        
        tavily_client = TavilyClient(api_key=tavily_api_key)
        response = tavily_client.search(
            query=query,
            max_results=max_results,
            search_depth="basic"
        )
        return response
    except Exception as e:
        return {"error": f"Search failed: {str(e)}"}

@tool(args_schema=CalculatorInput)
def calculator(expression: str) -> str:
    """
    Performs mathematical calculations on numbers.
    Useful for calculating percentages, differences, growth rates, and validating numerical data.
    IMPORTANT: Use this to verify calculations and ensure numerical accuracy in your analysis.
    """
    try:
        # Safe evaluation - only allow mathematical operations
        allowed_chars = set('0123456789+-*/(). ')
        if not all(c in allowed_chars for c in expression):
            return "Error: Invalid characters in expression. Only numbers and basic operators (+, -, *, /, parentheses) are allowed."
        
        result = eval(expression)
        return f"{expression} = {result}"
    except Exception as e:
        return f"Error calculating '{expression}': {str(e)}"

@tool
def current_date() -> str:
    """
    Returns the current date and time.
    ALWAYS use this at the start to establish temporal context for your research.
    Essential for determining if events/dates mentioned in other sources are current, upcoming, or historical.
    """
    now = datetime.now()
    return f"Current date: {now.strftime('%B %d, %Y')} (Year: {now.year}, Month: {now.month}, Day: {now.day})"

TOOLS: List[Callable[..., any]] = [
    current_date,
    search_web,
    calculator,
]

RISKY_TOOLS = {}  # guardrail: require confirmation