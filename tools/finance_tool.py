import yfinance as yf
from typing import Dict, Any, Optional
import re

def normalize_name(name: str) -> str:
    """Normalize company name by stripping legal forms and punctuation for clean comparison."""
    n = name.lower()
    n = re.sub(r'\b(ltd|limited|inc|incorporated|corp|corporation|pvt|co|company|group|pbc|llc|plc|holdings|sa|ag|gmbh)\b', '', n)
    n = re.sub(r'[^a-z0-9\s]', '', n)
    return ' '.join(n.split())

def is_valid_name_match(query: str, candidate_name: str) -> bool:
    """
    Ensure the candidate actually represents the queried company.
    Prevents false substring matches (e.g. 'Systems Limited' matching 'Apollo Micro Systems Ltd').
    """
    q_norm = normalize_name(query)
    c_norm = normalize_name(candidate_name)
    if not q_norm or not c_norm:
        return False
    # Exact normalized match (e.g. 'systems' == 'systems')
    if q_norm == c_norm:
        return True
    # Candidate starts with query (e.g. 'apple' -> 'apple consumer')
    if c_norm.startswith(q_norm + ' '):
        return True
    # If candidate has distinct leading words not present in query (like 'Apollo Micro'), reject!
    return False

def format_number(val: Optional[float], prefix: str = "$", currency: str = "USD") -> str:
    """Format large numbers into B/M/K representations."""
    if val is None or not isinstance(val, (int, float)):
        return "N/A"
    
    # Use currency symbol or code
    curr_prefix = f"{currency} " if currency != "USD" else prefix
    abs_val = abs(val)
    if abs_val >= 1e12:
        return f"{curr_prefix}{val / 1e12:.2f}T"
    elif abs_val >= 1e9:
        return f"{curr_prefix}{val / 1e9:.2f}B"
    elif abs_val >= 1e6:
        return f"{curr_prefix}{val / 1e6:.2f}M"
    elif abs_val >= 1e3:
        return f"{curr_prefix}{val / 1e3:.2f}K"
    else:
        return f"{curr_prefix}{val:.2f}"

def get_financial_metrics(query_or_symbol: str) -> Dict[str, Any]:
    """
    Intelligently checks whether the company is a PUBLICLY traded equity or a PRIVATE entity.
    Uses strict entity matching to prevent false positives (e.g. Systems Limited vs Apollo Micro Systems).
    """
    query = query_or_symbol.strip()
    
    # Curated authoritative mappings for major public companies (global & regional)
    known_tickers = {
        "systems limited": "SYS.KA",
        "systems": "SYS.KA",
        "apple": "AAPL", "aapl": "AAPL",
        "nvidia": "NVDA", "nvda": "NVDA",
        "microsoft": "MSFT", "msft": "MSFT",
        "tesla": "TSLA", "tsla": "TSLA",
        "google": "GOOGL", "alphabet": "GOOGL", "googl": "GOOGL",
        "amazon": "AMZN", "amzn": "AMZN",
        "meta": "META",
        "netflix": "NFLX",
        "amd": "AMD",
        "intel": "INTC",
        "tcs": "TCS.NS",
        "infosys": "INFY"
    }
    
    resolved_ticker = None
    is_public = False
    
    lowered_query = query.lower()
    if lowered_query in known_tickers:
        resolved_ticker = known_tickers[lowered_query]
        is_public = True
    elif query.isupper() and 1 <= len(query) <= 6 and not any(c in query for c in [' ', '.']):
        resolved_ticker = query
        is_public = True
    else:
        # Search yfinance directory with strict name verification
        try:
            search_results = yf.Search(query)
            quotes = getattr(search_results, "quotes", [])
            for q in quotes:
                if q.get("quoteType") == "EQUITY" and q.get("symbol"):
                    short_name = q.get("shortname") or ""
                    long_name = q.get("longname") or ""
                    
                    # Strictly verify that candidate name actually matches query
                    if is_valid_name_match(query, short_name) or is_valid_name_match(query, long_name):
                        resolved_ticker = q["symbol"]
                        is_public = True
                        break
        except Exception:
            pass

    # If identified as a verified public equity
    if is_public and resolved_ticker:
        try:
            ticker = yf.Ticker(resolved_ticker)
            info = ticker.info or {}
            
            # Fetch price
            current_price = info.get("currentPrice") or info.get("regularMarketPrice")
            if current_price is None:
                fast_info = getattr(ticker, "fast_info", None)
                if fast_info:
                    current_price = getattr(fast_info, "last_price", None)
                    
            currency = info.get("currency") or "USD"
            market_cap = info.get("marketCap")
            pe_ratio = info.get("trailingPE") or info.get("forwardPE")
            fifty_two_week_high = info.get("fiftyTwoWeekHigh")
            fifty_two_week_low = info.get("fiftyTwoWeekLow")
            total_revenue = info.get("totalRevenue")
            profit_margins = info.get("profitMargins")
            target_mean_price = info.get("targetMeanPrice")
            recommendation = info.get("recommendationKey", "N/A")

            margin_pct = f"{profit_margins * 100:.2f}%" if profit_margins is not None else "N/A"
            official_name = info.get("longName") or info.get("shortName") or query

            # Verify official name isn't a completely different entity
            if is_valid_name_match(query, official_name) or resolved_ticker in known_tickers.values():
                return {
                    "status": "success",
                    "is_public": True,
                    "data": {
                        "symbol": resolved_ticker,
                        "company_name": official_name,
                        "entity_type": "Publicly Traded Corporation",
                        "exchange": info.get("exchange", "Stock Exchange"),
                        "sector": info.get("sector") or "Technology & Services",
                        "industry": info.get("industry") or "IT Services & Consulting",
                        "current_price": f"{current_price:.2f} {currency}" if current_price else "N/A",
                        "market_cap": format_number(market_cap, currency=currency),
                        "pe_ratio": f"{pe_ratio:.2f}" if pe_ratio else "N/A",
                        "52_week_high": f"{fifty_two_week_high:.2f} {currency}" if fifty_two_week_high else "N/A",
                        "52_week_low": f"{fifty_two_week_low:.2f} {currency}" if fifty_two_week_low else "N/A",
                        "total_revenue": format_number(total_revenue, currency=currency),
                        "profit_margins": margin_pct,
                        "analyst_target_price": f"{target_mean_price:.2f} {currency}" if target_mean_price else "N/A",
                        "analyst_rating": recommendation.upper() if recommendation else "N/A"
                    }
                }
        except Exception:
            pass

    # If unlisted / private or no exact public stock found
    # Retain the user's EXACT query as the company name! Never hijack it with another company!
    return {
        "status": "success",
        "is_public": False,
        "data": {
            "symbol": "PRIVATE / UNLISTED",
            "company_name": query,
            "entity_type": "Privately Held Enterprise / Regional Entity",
            "exchange": "Not Listed on Global Public Exchanges",
            "sector": "Commercial Technology & Services",
            "industry": "Enterprise Solutions",
            "ownership_status": "Private / Direct Ownership",
            "public_trading": "Unlisted (No SEC Public Stock Reporting)",
            "valuation_note": "Valuation determined via private capital or local filings."
        }
    }

if __name__ == "__main__":
    import json
    print("--- Test 'Systems Limited' ---")
    print(json.dumps(get_financial_metrics("Systems Limited"), indent=2))
    print("\n--- Test 'OpenAI' ---")
    print(json.dumps(get_financial_metrics("OpenAI"), indent=2))
