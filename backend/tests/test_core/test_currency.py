"""
Tests for currency module - conversion, formatting, and validation.
"""

import pytest

from app.core.currency import (
    convert_currency,
    get_currency_symbol,
    format_currency,
    is_valid_currency,
    EXCHANGE_RATES,
    CURRENCIES,
)


# =============================================================================
# Currency Conversion Tests
# =============================================================================


class TestCurrencyConversion:
    """Test currency conversion functionality."""

    def test_convert_same_currency(self):
        """Test converting from currency to itself returns same amount."""
        assert convert_currency(100, "UGX", "UGX") == 100
        assert convert_currency(100, "USD", "USD") == 100
        assert convert_currency(100, "KES", "KES") == 100

    def test_convert_usd_to_ugx(self):
        """Test USD to UGX conversion."""
        # 1 USD = 3750 UGX
        result = convert_currency(100, "USD", "UGX")
        assert result == 375000.0

    def test_convert_ugx_to_usd(self):
        """Test UGX to USD conversion."""
        # 375000 UGX / 3750 = 100 USD
        result = convert_currency(375000, "UGX", "USD")
        assert result == 100.0

    def test_convert_kes_to_ugx(self):
        """Test KES to UGX conversion."""
        # 1 KES = 29 UGX
        result = convert_currency(100, "KES", "UGX")
        assert result == 2900.0

    def test_convert_tzs_to_ugx(self):
        """Test TZS to UGX conversion."""
        # 1 TZS = 1.5 UGX
        result = convert_currency(100, "TZS", "UGX")
        assert result == 150.0

    def test_convert_rwf_to_ugx(self):
        """Test RWF to UGX conversion."""
        # 1 RWF = 2.9 UGX
        result = convert_currency(100, "RWF", "UGX")
        assert result == 290.0

    def test_convert_eur_to_ugx(self):
        """Test EUR to UGX conversion."""
        # 1 EUR = 4100 UGX
        result = convert_currency(100, "EUR", "UGX")
        assert result == 410000.0

    def test_convert_gbp_to_ugx(self):
        """Test GBP to UGX conversion."""
        # 1 GBP = 4800 UGX
        result = convert_currency(100, "GBP", "UGX")
        assert result == 480000.0

    def test_convert_between_african_currencies(self):
        """Test converting between African currencies (not via UGX)."""
        # 100 KES to TZS
        # Step 1: 100 KES * 29 = 2900 UGX
        # Step 2: 2900 UGX / 1.5 = 1933.33 TZS
        result = convert_currency(100, "KES", "TZS")
        assert result == 1933.33

    def test_convert_rounding(self):
        """Test that results are rounded to 2 decimal places."""
        result = convert_currency(1, "TZS", "KES")
        # 1 TZS * 1.5 = 1.5 UGX
        # 1.5 UGX / 29 = 0.0517... KES
        # Rounded to 2 decimals: 0.05
        assert result == 0.05

    def test_convert_zero_amount(self):
        """Test converting zero amount."""
        assert convert_currency(0, "USD", "UGX") == 0.0

    def test_convert_negative_amount(self):
        """Test converting negative amount."""
        # Negative amounts should work (for refunds/adjustments)
        assert convert_currency(-100, "USD", "UGX") == -375000.0

    def test_convert_unknown_currency_defaults_to_1(self):
        """Test converting with unknown currency defaults to rate 1.0."""
        result = convert_currency(100, "XYZ", "UGX")
        assert result == 100.0  # XYZ defaults to 1.0 rate

        result = convert_currency(100, "UGX", "XYZ")
        assert result == 100.0  # XYZ defaults to 1.0 rate

    def test_convert_decimal_amounts(self):
        """Test converting decimal amounts."""
        result = convert_currency(50.5, "USD", "UGX")
        # 50.5 * 3750 = 189375
        assert result == 189375.0

    def test_convert_very_large_amount(self):
        """Test converting very large amounts."""
        result = convert_currency(1000000, "USD", "UGX")
        assert result == 3750000000.0

    def test_convert_very_small_amount(self):
        """Test converting very small amounts."""
        result = convert_currency(0.01, "USD", "UGX")
        # 0.01 * 3750 = 37.5
        assert result == 37.5


# =============================================================================
# Currency Symbol Tests
# =============================================================================


class TestCurrencySymbols:
    """Test currency symbol functionality."""

    def test_get_symbol_usd(self):
        """Test USD symbol."""
        assert get_currency_symbol("USD") == "$"

    def test_get_symbol_eur(self):
        """Test EUR symbol."""
        assert get_currency_symbol("EUR") == "€"

    def test_get_symbol_gbp(self):
        """Test GBP symbol."""
        assert get_currency_symbol("GBP") == "£"

    def test_get_symbol_ugx(self):
        """Test UGX symbol (returns code for African currencies)."""
        assert get_currency_symbol("UGX") == "UGX"

    def test_get_symbol_kes(self):
        """Test KES symbol."""
        assert get_currency_symbol("KES") == "KES"

    def test_get_symbol_unknown(self):
        """Test unknown currency returns code as symbol."""
        assert get_currency_symbol("XYZ") == "XYZ"

    def test_all_currencies_have_symbols(self):
        """Test all supported currencies have symbols."""
        for currency in CURRENCIES:
            symbol = get_currency_symbol(currency["code"])
            assert symbol is not None
            assert len(symbol) > 0


# =============================================================================
# Currency Formatting Tests
# =============================================================================


class TestCurrencyFormatting:
    """Test currency formatting functionality."""

    def test_format_usd(self):
        """Test USD formatting with symbol first."""
        result = format_currency(1500.50, "USD")
        assert result == "$1,500.50"

    def test_format_eur(self):
        """Test EUR formatting with symbol first."""
        result = format_currency(1500.50, "EUR")
        assert result == "€1,500.50"

    def test_format_gbp(self):
        """Test GBP formatting with symbol first."""
        result = format_currency(1500.50, "GBP")
        assert result == "£1,500.50"

    def test_format_ugx(self):
        """Test UGX formatting with code first and no decimals."""
        result = format_currency(1500000, "UGX")
        assert result == "UGX 1,500,000"

    def test_format_kes(self):
        """Test KES formatting."""
        result = format_currency(50000, "KES")
        assert result == "KES 50,000"

    def test_format_tzs(self):
        """Test TZS formatting."""
        result = format_currency(100000, "TZS")
        assert result == "TZS 100,000"

    def test_format_rwf(self):
        """Test RWF formatting."""
        result = format_currency(75000, "RWF")
        assert result == "RWF 75,000"

    def test_format_zero(self):
        """Test formatting zero amount."""
        assert format_currency(0, "USD") == "$0.00"
        assert format_currency(0, "UGX") == "UGX 0"

    def test_format_with_decimals_african(self):
        """Test African currencies ignore decimals in display."""
        result = format_currency(1500.99, "UGX")
        assert result == "UGX 1,501"  # Rounded to 0 decimals

    def test_format_negative(self):
        """Test formatting negative amounts."""
        assert format_currency(-100, "USD") == "$-100.00"
        assert format_currency(-100, "UGX") == "UGX -100"

    def test_format_thousand_separators(self):
        """Test thousand separators work correctly."""
        # Test various amounts
        assert format_currency(1000, "USD") == "$1,000.00"
        assert format_currency(1000000, "USD") == "$1,000,000.00"
        assert format_currency(1234567890, "USD") == "$1,234,567,890.00"


# =============================================================================
# Currency Validation Tests
# =============================================================================


class TestCurrencyValidation:
    """Test currency validation functionality."""

    def test_is_valid_currency_supported(self):
        """Test all supported currencies are valid."""
        supported = ["UGX", "USD", "KES", "TZS", "RWF", "EUR", "GBP"]
        for currency in supported:
            assert is_valid_currency(currency) is True

    def test_is_valid_currency_unknown(self):
        """Test unknown currencies are invalid."""
        assert is_valid_currency("XYZ") is False
        assert is_valid_currency("ABC") is False
        assert is_valid_currency("INVALID") is False

    def test_is_valid_currency_case_sensitive(self):
        """Test currency codes are case sensitive."""
        assert is_valid_currency("usd") is False
        assert is_valid_currency("ugx") is False
        assert is_valid_currency("Usd") is False

    def test_is_valid_currency_empty(self):
        """Test empty string is invalid."""
        assert is_valid_currency("") is False

    def test_is_valid_currency_none(self):
        """Test None is invalid."""
        with pytest.raises(TypeError):
            is_valid_currency(None)


# =============================================================================
# Exchange Rates Tests
# =============================================================================


class TestExchangeRates:
    """Test exchange rates data structure."""

    def test_exchange_rates_is_dict(self):
        """Test EXCHANGE_RATES is a dictionary."""
        assert isinstance(EXCHANGE_RATES, dict)

    def test_exchange_rates_has_base_currency(self):
        """Test UGX (base currency) has rate 1.0."""
        assert EXCHANGE_RATES["UGX"] == 1.0

    def test_exchange_rates_all_positive(self):
        """Test all exchange rates are positive numbers."""
        for currency, rate in EXCHANGE_RATES.items():
            assert rate > 0, f"Rate for {currency} should be positive"

    def test_currencies_list_matches_exchange_rates(self):
        """Test CURRENCIES list matches EXCHANGE_RATES keys."""
        currency_codes = [c["code"] for c in CURRENCIES]
        rate_codes = list(EXCHANGE_RATES.keys())

        assert set(currency_codes) == set(rate_codes)

    def test_currencies_have_required_fields(self):
        """Test all currency entries have required fields."""
        required_fields = ["code", "symbol", "name"]
        for currency in CURRENCIES:
            for field in required_fields:
                assert field in currency
                assert currency[field] is not None
                assert len(currency[field]) > 0


# =============================================================================
# Real-World Use Case Tests
# =============================================================================


class TestRealWorldUseCases:
    """Test real-world scenarios for currency handling."""

    def test_tenant_rent_conversion(self):
        """Test converting tenant rent from USD to local currency."""
        # A tenant pays $500 rent
        rent_usd = 500

        # Convert to various African currencies
        ugx = convert_currency(rent_usd, "USD", "UGX")
        kes = convert_currency(rent_usd, "USD", "KES")
        tzs = convert_currency(rent_usd, "USD", "TZS")

        # Verify conversions
        assert ugx == 1875000.0  # 500 * 3750
        assert kes == 64741.38  # 1875000 / 29
        assert tzs == 1250000.0  # 1875000 / 1.5

    def test_payment_display_formatting(self):
        """Test displaying payments in different formats."""
        payment_amount = 2500000  # 2.5M UGX

        # Display in UGX
        ugx_display = format_currency(payment_amount, "UGX")
        assert ugx_display == "UGX 2,500,000"

        # Convert and display in USD
        usd_amount = convert_currency(payment_amount, "UGX", "USD")
        usd_display = format_currency(usd_amount, "USD")
        assert usd_display == "$666.67"

    def test_multi_currency_property(self):
        """Test handling property with different tenant currencies."""
        # Property rents in different currencies
        rents = {
            "UGX": 1500000,
            "KES": 45000,
            "USD": 400,
        }

        # Convert all to UGX for comparison
        ugx_equivalents = {
            currency: convert_currency(amount, currency, "UGX")
            for currency, amount in rents.items()
        }

        assert ugx_equivalents["UGX"] == 1500000.0
        assert ugx_equivalents["KES"] == 1305000.0  # 45000 * 29
        assert ugx_equivalents["USD"] == 1500000.0  # 400 * 3750

    def test_currency_validation_in_form(self):
        """Test validating currency input from form."""
        # Simulate form input validation
        user_input = "UGX"
        assert is_valid_currency(user_input)

        # Invalid input
        invalid_input = "XYZ"
        assert not is_valid_currency(invalid_input)
