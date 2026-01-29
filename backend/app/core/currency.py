"""
Currency conversion utilities for LandTen.

Exchange rates are relative to UGX (Ugandan Shilling) as the base currency.
For MVP, rates are static. Future: integrate with live rates API.
"""

from typing import Dict

# Exchange rates: How many UGX equals 1 unit of each currency
# Example: 1 USD = 3,750 UGX
EXCHANGE_RATES: Dict[str, float] = {
    "UGX": 1.0,  # Base currency
    "USD": 3750.0,  # 1 USD = 3,750 UGX
    "KES": 29.0,  # 1 KES = 29 UGX
    "TZS": 1.5,  # 1 TZS = 1.5 UGX
    "RWF": 2.9,  # 1 RWF = 2.9 UGX
    "EUR": 4100.0,  # 1 EUR = 4,100 UGX
    "GBP": 4800.0,  # 1 GBP = 4,800 UGX
}

# Supported currencies with display info
CURRENCIES = [
    {"code": "UGX", "symbol": "UGX", "name": "Ugandan Shilling"},
    {"code": "USD", "symbol": "$", "name": "US Dollar"},
    {"code": "KES", "symbol": "KES", "name": "Kenyan Shilling"},
    {"code": "TZS", "symbol": "TZS", "name": "Tanzanian Shilling"},
    {"code": "RWF", "symbol": "RWF", "name": "Rwandan Franc"},
    {"code": "EUR", "symbol": "€", "name": "Euro"},
    {"code": "GBP", "symbol": "£", "name": "British Pound"},
]


def convert_currency(amount: float, from_currency: str, to_currency: str) -> float:
    """
    Convert an amount from one currency to another.

    Args:
        amount: The amount to convert
        from_currency: Source currency code (e.g., "USD")
        to_currency: Target currency code (e.g., "UGX")

    Returns:
        Converted amount rounded to 2 decimal places

    Example:
        convert_currency(100, "USD", "UGX") -> 375000.0
        convert_currency(375000, "UGX", "USD") -> 100.0
    """
    if from_currency == to_currency:
        return amount

    # Get exchange rates, default to 1.0 if unknown currency
    from_rate = EXCHANGE_RATES.get(from_currency, 1.0)
    to_rate = EXCHANGE_RATES.get(to_currency, 1.0)

    # Convert: amount in source -> UGX -> target
    # Step 1: Convert to UGX (multiply by source rate)
    ugx_amount = amount * from_rate
    # Step 2: Convert from UGX to target (divide by target rate)
    result = ugx_amount / to_rate

    return round(result, 2)


def get_currency_symbol(currency_code: str) -> str:
    """Get the display symbol for a currency code."""
    for currency in CURRENCIES:
        if currency["code"] == currency_code:
            return currency["symbol"]
    return currency_code


def format_currency(amount: float, currency_code: str) -> str:
    """
    Format an amount with its currency symbol.

    Args:
        amount: The amount to format
        currency_code: Currency code (e.g., "UGX")

    Returns:
        Formatted string (e.g., "UGX 1,500,000" or "$400")
    """
    symbol = get_currency_symbol(currency_code)

    # Format with thousand separators
    if currency_code in ["USD", "EUR", "GBP"]:
        # For these currencies, symbol comes first
        return f"{symbol}{amount:,.2f}"
    else:
        # For African currencies, code comes first with space
        return f"{symbol} {amount:,.0f}"


def is_valid_currency(currency_code: str) -> bool:
    """Check if a currency code is supported."""
    return currency_code in EXCHANGE_RATES
