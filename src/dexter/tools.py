from langchain.tools import tool
from typing import List, Callable
import os
from datetime import datetime
from pydantic import BaseModel, Field
from tavily import TavilyClient
import yfinance as yf

####################################
# Tools
####################################

# Tavily search counter (persiste durante la sesión)
_tavily_search_count = 0

def _get_tavily_limit() -> int:
    """Obtiene el límite de búsquedas desde variables de entorno."""
    limit = os.getenv("TAVILY_MAX_SEARCHES_PER_SESSION")
    if limit:
        try:
            return int(limit)
        except ValueError:
            pass
    return None  # Sin límite por defecto

def _check_tavily_limit() -> tuple[bool, str]:
    """
    Verifica si se puede hacer otra búsqueda.
    Returns: (can_search, message)
    """
    global _tavily_search_count
    limit = _get_tavily_limit()
    
    if limit is None:
        return True, ""
    
    if _tavily_search_count >= limit:
        return False, f"Límite de búsquedas alcanzado ({_tavily_search_count}/{limit}). Configura TAVILY_MAX_SEARCHES_PER_SESSION para cambiar el límite."
    
    remaining = limit - _tavily_search_count
    return True, f"Búsquedas restantes: {remaining}/{limit}"

def _increment_tavily_count():
    """Incrementa el contador de búsquedas."""
    global _tavily_search_count
    _tavily_search_count += 1

class WebSearchInput(BaseModel):
    query: str = Field(description="The search query to look up on the internet. Be specific and include relevant keywords for better results.")
    max_results: int = Field(default=5, description="Maximum number of search results to return. Default is 5.")

class CalculatorInput(BaseModel):
    expression: str = Field(description="A mathematical expression to calculate. Examples: '435.15 - 349.07', '(100 / 50) * 2', '15.5 + 20.3'")

class StockInfoInput(BaseModel):
    ticker: str = Field(description="The stock ticker symbol. Examples: 'AAPL', 'GOOGL', 'MSFT', 'TSLA', '0700.HK'")

@tool(args_schema=WebSearchInput)
def search_web(query: str, max_results: int = 5) -> dict:
    """
    Searches the internet for information using Tavily API.
    Useful for finding recent news, articles, analysis, and general information about any topic.
    Returns a list of relevant web pages with titles, URLs, and content snippets.
    """
    # Verificar límite de búsquedas
    can_search, message = _check_tavily_limit()
    if not can_search:
        return {"error": message}
    
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
        
        # Incrementar contador después de búsqueda exitosa
        _increment_tavily_count()
        
        # Agregar info del límite a la respuesta si está configurado
        if message:
            response["_search_limit_info"] = message
        
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

@tool(args_schema=StockInfoInput)
def get_stock_info(ticker: str) -> dict:
    """
    Gets comprehensive stock information from Yahoo Finance including current price, market data, and company details.
    Useful for analyzing stocks, ETFs, and market indices. Supports global markets.
    Returns current price, market cap, PE ratio, dividends, 52-week range, volume, and more.
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Extract key information
        result = {
            "ticker": ticker.upper(),
            "name": info.get("longName", info.get("shortName", "N/A")),
            "current_price": info.get("currentPrice", info.get("regularMarketPrice", "N/A")),
            "currency": info.get("currency", "N/A"),
            "market_cap": info.get("marketCap", "N/A"),
            "pe_ratio": info.get("trailingPE", "N/A"),
            "forward_pe": info.get("forwardPE", "N/A"),
            "dividend_yield": info.get("dividendYield", "N/A"),
            "52_week_high": info.get("fiftyTwoWeekHigh", "N/A"),
            "52_week_low": info.get("fiftyTwoWeekLow", "N/A"),
            "50_day_avg": info.get("fiftyDayAverage", "N/A"),
            "200_day_avg": info.get("twoHundredDayAverage", "N/A"),
            "volume": info.get("volume", "N/A"),
            "avg_volume": info.get("averageVolume", "N/A"),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "exchange": info.get("exchange", "N/A"),
        }
        
        return result
    except Exception as e:
        return {"error": f"Failed to get stock info for {ticker}: {str(e)}"}

TOOLS: List[Callable[..., any]] = [
    current_date,
    search_web,
    calculator,
    get_stock_info,
]

RISKY_TOOLS = {}  # guardrail: require confirmation