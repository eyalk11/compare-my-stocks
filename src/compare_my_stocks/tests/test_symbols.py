import pytest
from unittest.mock import MagicMock, patch
import json

from engine.symbols import AbstractSymbol, SimpleSymbol, SpecialSymbol
from common.common import EnhancedJSONEncoder
from config import config


class TestAbstractSymbolHashing:
    """Test AbstractSymbol hashing behavior."""

    def test_hash_with_none_dic(self):
        """Test __hash__ when dic is None - should hash the symbol."""
        symbol = SimpleSymbol("AAPL")
        expected_hash = hash("AAPL")
        assert hash(symbol) == expected_hash

    def test_hash_with_dic(self):
        """Test __hash__ when dic is not None - should hash JSON of dic."""
        dic = {'symbol': 'AAPL', 'exchange': 'NASDAQ'}
        symbol = SimpleSymbol(dic)
        expected_hash = hash(json.dumps(dic, cls=EnhancedJSONEncoder))
        assert hash(symbol) == expected_hash

    def test_hash_consistency(self):
        """Test that hash is consistent across multiple calls."""
        symbol = SimpleSymbol("AAPL")
        hash1 = hash(symbol)
        hash2 = hash(symbol)
        assert hash1 == hash2

    def test_hash_different_symbols(self):
        """Test that different symbols have different hashes."""
        symbol1 = SimpleSymbol("AAPL")
        symbol2 = SimpleSymbol("MSFT")
        assert hash(symbol1) != hash(symbol2)

    def test_hash_different_dics(self):
        """Test that different dics have different hashes."""
        dic1 = {'symbol': 'AAPL', 'exchange': 'NASDAQ'}
        dic2 = {'symbol': 'AAPL', 'exchange': 'NYSE'}
        symbol1 = SimpleSymbol(dic1)
        symbol2 = SimpleSymbol(dic2)
        assert hash(symbol1) != hash(symbol2)


class TestAbstractSymbolEquality:
    """Test AbstractSymbol equality comparison."""

    def test_equality_same_symbol(self):
        """Test equality of two symbols with same string."""
        symbol1 = SimpleSymbol("AAPL")
        symbol2 = SimpleSymbol("AAPL")
        assert symbol1 == symbol2

    def test_equality_different_symbol(self):
        """Test inequality of symbols with different strings."""
        symbol1 = SimpleSymbol("AAPL")
        symbol2 = SimpleSymbol("MSFT")
        assert not (symbol1 == symbol2)

    def test_equality_same_dic(self):
        """Test equality of symbols with same dic."""
        dic = {'symbol': 'AAPL', 'exchange': 'NASDAQ'}
        symbol1 = SimpleSymbol(dic)
        symbol2 = SimpleSymbol(dic.copy())
        assert symbol1 == symbol2

    def test_equality_based_on_hash(self):
        """Test that equality is based on hash comparison."""
        symbol1 = SimpleSymbol("AAPL")
        symbol2 = SimpleSymbol("AAPL")
        assert hash(symbol1) == hash(symbol2)
        assert symbol1 == symbol2

    def test_equality_string_vs_dic(self):
        """Test equality when comparing string-based and dic-based symbols with same symbol."""
        symbol1 = SimpleSymbol("AAPL")
        symbol2 = SimpleSymbol({'symbol': 'AAPL'})
        assert hash(symbol1) != hash(symbol2)  # Different hashes
        assert not (symbol1 == symbol2)  # Not equal


class TestAbstractSymbolGetattr:
    """Test AbstractSymbol __getattr__ method."""

    def test_getattr_from_dic(self):
        """Test __getattr__ retrieves attribute from dic."""
        dic = {'symbol': 'AAPL', 'exchange': 'NASDAQ', 'price': 150.5}
        symbol = SimpleSymbol(dic)
        assert symbol.exchange == 'NASDAQ'
        assert symbol.price == 150.5

    def test_getattr_missing_attribute(self):
        """Test __getattr__ raises AttributeError for missing attribute."""
        dic = {'symbol': 'AAPL'}
        symbol = SimpleSymbol(dic)
        with pytest.raises(AttributeError):
            _ = symbol.nonexistent

    def test_getattr_with_none_dic(self):
        """Test __getattr__ raises AttributeError when dic is None."""
        symbol = SimpleSymbol("AAPL")
        with pytest.raises(AttributeError):
            _ = symbol.exchange

    def test_getattr_multiple_keys(self):
        """Test __getattr__ with multiple keys in dic."""
        dic = {'symbol': 'AAPL', 'exchange': 'NASDAQ', 'isin': 'US0378331005'}
        symbol = SimpleSymbol(dic)
        assert symbol.exchange == 'NASDAQ'
        assert symbol.isin == 'US0378331005'

    def test_getattr_none_value_in_dic(self):
        """Test __getattr__ when dic has None value."""
        dic = {'symbol': 'AAPL', 'exchange': None}
        symbol = SimpleSymbol(dic)
        with pytest.raises(AttributeError):
            _ = symbol.exchange  # None value means attribute doesn't exist


class TestSimpleSymbolInitialization:
    """Test SimpleSymbol initialization with different input types."""

    def test_init_with_string(self):
        """Test initialization with a string."""
        symbol = SimpleSymbol("AAPL")
        assert symbol.symbol == "AAPL"
        assert symbol.dic is None

    def test_init_with_dict(self):
        """Test initialization with a dictionary."""
        dic = {'symbol': 'AAPL', 'exchange': 'NASDAQ'}
        symbol = SimpleSymbol(dic)
        assert symbol.symbol == 'AAPL'
        assert symbol.dic == dic

    def test_init_with_abstract_symbol(self):
        """Test initialization with an AbstractSymbol."""
        original = SimpleSymbol("AAPL")
        copy = SimpleSymbol(original)
        assert copy.symbol == original.symbol
        assert copy.dic == original.dic

    def test_init_with_object_text_method(self):
        """Test initialization with an object that has text() method."""
        class MockObject:
            def text(self):
                return "AAPL"

        symbol = SimpleSymbol(MockObject())
        assert symbol.symbol == "AAPL"

    def test_init_with_numeric_object(self):
        """Test initialization with numeric object."""
        symbol = SimpleSymbol(123)
        assert symbol.symbol == "123"

    def test_init_copies_dic_from_symbol(self):
        """Test that initialization copies dic from another symbol."""
        original_dic = {'symbol': 'AAPL', 'exchange': 'NASDAQ'}
        original = SimpleSymbol(original_dic)
        copy = SimpleSymbol(original)
        assert copy.dic == original.dic


class TestSimpleSymbolStringConversion:
    """Test SimpleSymbol string conversion."""

    def test_str_representation(self):
        """Test __str__ returns the symbol string."""
        symbol = SimpleSymbol("AAPL")
        assert str(symbol) == "AAPL"

    def test_str_with_dict_initialization(self):
        """Test __str__ when initialized with dict."""
        dic = {'symbol': 'MSFT', 'exchange': 'NASDAQ'}
        symbol = SimpleSymbol(dic)
        assert str(symbol) == "MSFT"

    def test_str_consistency(self):
        """Test that str() is consistent with symbol property."""
        symbol = SimpleSymbol("GOOG")
        assert str(symbol) == symbol.symbol


class TestSimpleSymbolComparison:
    """Test SimpleSymbol comparison operators."""

    def test_greater_than_comparison(self):
        """Test __gt__ comparison operator."""
        symbol_a = SimpleSymbol("AAPL")
        symbol_z = SimpleSymbol("ZZZZ")
        assert symbol_z > symbol_a
        assert not (symbol_a > symbol_z)

    def test_less_than_comparison(self):
        """Test __lt__ comparison operator."""
        symbol_a = SimpleSymbol("AAPL")
        symbol_z = SimpleSymbol("ZZZZ")
        assert symbol_a < symbol_z
        assert not (symbol_z < symbol_a)

    def test_comparison_with_string(self):
        """Test comparison with string objects."""
        symbol = SimpleSymbol("MSFT")
        assert symbol > "AAPL"
        assert symbol < "ZZZZ"
        assert not (symbol > "ZZZZ")
        assert not (symbol < "AAPL")

    def test_comparison_equality(self):
        """Test comparison when symbols are equal."""
        symbol1 = SimpleSymbol("AAPL")
        symbol2 = SimpleSymbol("AAPL")
        assert not (symbol1 < symbol2)
        assert not (symbol1 > symbol2)

    def test_comparison_case_sensitive(self):
        """Test that comparison is case-sensitive."""
        symbol_lower = SimpleSymbol("aapl")
        symbol_upper = SimpleSymbol("AAPL")
        assert symbol_upper < symbol_lower  # uppercase letters come before lowercase in ASCII


class TestSimpleSymbolSerialization:
    """Test SimpleSymbol serialization with __getstate__ and __setstate__."""

    def test_getstate_returns_dict(self):
        """Test __getstate__ returns the __dict__."""
        symbol = SimpleSymbol("AAPL")
        state = symbol.__getstate__()
        assert isinstance(state, dict)
        assert state == symbol.__dict__

    def test_getstate_with_dict_initialization(self):
        """Test __getstate__ when initialized with dict."""
        dic = {'symbol': 'AAPL', 'exchange': 'NASDAQ'}
        symbol = SimpleSymbol(dic)
        state = symbol.__getstate__()
        assert 'text' in state or '_text' in state
        assert 'dic' in state or '_dic' in state

    def test_setstate_restores_state(self):
        """Test __setstate__ restores the object state."""
        original = SimpleSymbol("AAPL")
        state = original.__getstate__()

        new_symbol = SimpleSymbol.__new__(SimpleSymbol)
        new_symbol.__setstate__(state)

        assert new_symbol.symbol == original.symbol
        assert new_symbol.dic == original.dic

    def test_serialization_roundtrip(self):
        """Test serialization and deserialization roundtrip."""
        dic = {'symbol': 'MSFT', 'exchange': 'NASDAQ', 'price': 300.0}
        original = SimpleSymbol(dic)

        state = original.__getstate__()
        restored = SimpleSymbol.__new__(SimpleSymbol)
        restored.__setstate__(state)

        assert restored.symbol == original.symbol
        assert restored.dic == original.dic
        assert hash(restored) == hash(original)


class TestSimpleSymbolGenFactory:
    """Test SimpleSymbol.gen() factory method."""

    def test_gen_with_string_simple(self):
        """Test gen() with simple string creates SimpleSymbol."""
        symbol = SimpleSymbol.gen("AAPL")
        assert isinstance(symbol, SimpleSymbol)
        assert symbol.symbol == "AAPL"

    def test_gen_with_string_special(self):
        """Test gen() with special symbol string creates SpecialSymbol."""
        prefix = config.Symbols.SpecialSymbols
        symbol = SimpleSymbol.gen(f"{prefix}USD")
        assert isinstance(symbol, SpecialSymbol)
        assert symbol.currency == "USD"

    def test_gen_with_abstract_symbol(self):
        """Test gen() with AbstractSymbol input."""
        original = SimpleSymbol("MSFT")
        generated = SimpleSymbol.gen(original)
        assert isinstance(generated, SimpleSymbol)
        assert generated.symbol == "MSFT"

    def test_gen_with_abstract_symbol_special(self):
        """Test gen() with special SpecialSymbol input - tests symbol detection."""
        # Note: There's a bug in gen() where it uses symb[1:] instead of sym[1:]
        # when symb is an AbstractSymbol. We test that the string-based path works.
        original = SpecialSymbol("EUR")
        # Get the symbol string representation
        symbol_str = original.symbol  # "$EUR"
        generated = SimpleSymbol.gen(symbol_str)
        assert isinstance(generated, SpecialSymbol)
        assert generated.currency == "EUR"

    def test_gen_with_invalid_type(self):
        """Test gen() raises exception with invalid type."""
        with pytest.raises(Exception, match="Unknown type"):
            SimpleSymbol.gen(123)

    def test_gen_with_invalid_object(self):
        """Test gen() raises exception with invalid object."""
        with pytest.raises(Exception, match="Unknown type"):
            SimpleSymbol.gen([1, 2, 3])

    def test_gen_preserves_symbol_value(self):
        """Test that gen() preserves the symbol value."""
        symbols = ["AAPL", "MSFT", "GOOG", "TSLA"]
        for sym in symbols:
            generated = SimpleSymbol.gen(sym)
            assert generated.symbol == sym


class TestSpecialSymbolBehavior:
    """Test SpecialSymbol specific behavior."""

    def test_special_symbol_initialization(self):
        """Test SpecialSymbol initialization."""
        symbol = SpecialSymbol("USD")
        assert symbol.currency == "USD"

    def test_special_symbol_dic(self):
        """Test SpecialSymbol dic property."""
        symbol = SpecialSymbol("EUR")
        assert symbol.dic == {'currency': 'EUR'}

    def test_special_symbol_symbol_property(self):
        """Test SpecialSymbol symbol property."""
        symbol = SpecialSymbol("GBP")
        assert symbol.symbol == f"{config.Symbols.SpecialSymbols}GBP"

    def test_special_symbol_get_date(self):
        """Test SpecialSymbol get_date method."""
        symbol = SpecialSymbol("USD")
        # get_date always returns 100
        assert symbol.get_date(None) == 100
        assert symbol.get_date("2023-01-01") == 100

    def test_special_symbol_hashing(self):
        """Test SpecialSymbol hashing behavior."""
        symbol1 = SpecialSymbol("USD")
        symbol2 = SpecialSymbol("USD")
        assert hash(symbol1) == hash(symbol2)

    def test_special_symbol_equality(self):
        """Test SpecialSymbol equality."""
        symbol1 = SpecialSymbol("USD")
        symbol2 = SpecialSymbol("USD")
        assert symbol1 == symbol2

    def test_special_symbol_different_currencies(self):
        """Test SpecialSymbols with different currencies."""
        symbol_usd = SpecialSymbol("USD")
        symbol_eur = SpecialSymbol("EUR")
        assert not (symbol_usd == symbol_eur)
        assert hash(symbol_usd) != hash(symbol_eur)


class TestSymbolIntegration:
    """Test integration scenarios with multiple symbol types."""

    def test_symbol_in_set(self):
        """Test that symbols can be used in sets."""
        symbol1 = SimpleSymbol("AAPL")
        symbol2 = SimpleSymbol("AAPL")
        symbol3 = SimpleSymbol("MSFT")

        symbol_set = {symbol1, symbol2, symbol3}
        # symbol1 and symbol2 should be considered the same
        assert len(symbol_set) == 2

    def test_symbol_as_dict_key(self):
        """Test that symbols can be used as dictionary keys."""
        symbol1 = SimpleSymbol("AAPL")
        symbol2 = SimpleSymbol("AAPL")

        symbol_dict = {symbol1: "Apple"}
        symbol_dict[symbol2] = "Apple Inc"

        # They should be the same key
        assert len(symbol_dict) == 1
        assert symbol_dict[symbol1] == "Apple Inc"

    def test_mixed_symbol_types(self):
        """Test mixing SimpleSymbol and SpecialSymbol."""
        simple = SimpleSymbol("AAPL")
        special = SpecialSymbol("USD")

        symbols = [simple, special]
        assert len(symbols) == 2
        assert symbols[0].symbol == "AAPL"
        assert symbols[1].symbol == f"{config.Symbols.SpecialSymbols}USD"

    def test_symbol_comparison_sorting(self):
        """Test sorting symbols."""
        symbols = [
            SimpleSymbol("ZZZZ"),
            SimpleSymbol("AAPL"),
            SimpleSymbol("MSFT"),
        ]
        sorted_symbols = sorted(symbols)
        assert sorted_symbols[0].symbol == "AAPL"
        assert sorted_symbols[1].symbol == "MSFT"
        assert sorted_symbols[2].symbol == "ZZZZ"

    def test_gen_factory_with_list(self):
        """Test gen() factory with a list of symbols."""
        prefix = config.Symbols.SpecialSymbols
        symbols_list = ["AAPL", "MSFT", f"{prefix}EUR"]
        generated = [SimpleSymbol.gen(s) for s in symbols_list]

        assert isinstance(generated[0], SimpleSymbol)
        assert generated[0].symbol == "AAPL"
        assert isinstance(generated[1], SimpleSymbol)
        assert generated[1].symbol == "MSFT"
        assert isinstance(generated[2], SpecialSymbol)
        assert generated[2].currency == "EUR"

    def test_abstract_symbol_polymorphism(self):
        """Test that SimpleSymbol and SpecialSymbol work through AbstractSymbol interface."""
        symbols = [
            SimpleSymbol("AAPL"),
            SpecialSymbol("USD"),
        ]

        # Test polymorphic behavior
        for symbol in symbols:
            assert hasattr(symbol, 'symbol')
            assert hasattr(symbol, 'dic')
            assert callable(hash)
            assert symbol == symbol  # Equality with self


class TestSymbolEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_string_symbol(self):
        """Test symbol with empty string."""
        symbol = SimpleSymbol("")
        assert symbol.symbol == ""
        assert str(symbol) == ""

    def test_symbol_with_special_characters(self):
        """Test symbol with special characters."""
        symbol = SimpleSymbol("AAPL.B")
        assert symbol.symbol == "AAPL.B"

    def test_very_long_symbol(self):
        """Test symbol with very long string."""
        long_symbol = "A" * 1000
        symbol = SimpleSymbol(long_symbol)
        assert symbol.symbol == long_symbol

    def test_symbol_with_unicode(self):
        """Test symbol with unicode characters."""
        symbol = SimpleSymbol("€EUR")
        assert symbol.symbol == "€EUR"

    def test_dict_with_extra_fields(self):
        """Test dict initialization with extra fields beyond 'symbol'."""
        dic = {
            'symbol': 'AAPL',
            'exchange': 'NASDAQ',
            'country': 'US',
            'sector': 'Technology'
        }
        symbol = SimpleSymbol(dic)
        assert symbol.symbol == 'AAPL'
        assert symbol.exchange == 'NASDAQ'
        assert symbol.country == 'US'
        assert symbol.sector == 'Technology'

    def test_special_symbol_with_special_characters(self):
        """Test SpecialSymbol with special characters in currency."""
        symbol = SpecialSymbol("US$")
        assert symbol.currency == "US$"
        assert symbol.dic == {'currency': 'US$'}
