import pytest
from datetime import datetime, date
import pytz
import logging

from common.common import (
    really_close,
    assert_not_none,
    c,
    rc,
    subdates,
    timeit,
    localize_it,
    unlocalize_it,
    Types,
    UniteType,
    tzawareness,
)


# Tests for really_close function
def test_really_close_equal_values():
    """Test that equal values are considered close."""
    assert really_close(10, 10)


def test_really_close_with_tolerance():
    """Test values within tolerance (1/1000 of value)."""
    # For value 1000, tolerance is 1
    assert really_close(1000, 1000.5)
    assert really_close(1000, 999.5)


def test_really_close_beyond_tolerance():
    """Test values beyond tolerance are not close."""
    # For value 1000, tolerance is 1, so difference of 2 should fail
    assert not really_close(1000, 998)


def test_really_close_zero_handling():
    """Test really_close with zero values."""
    # When k=0, tolerance is 1/1000 = 0.001
    assert really_close(0, 0)
    assert really_close(0, 0.0005)
    assert not really_close(0, 0.002)


def test_really_close_negative_values():
    """Test really_close with negative values."""
    assert really_close(-1000, -1000.5)
    assert really_close(-1000, -999.5)


def test_really_close_mixed_signs():
    """Test really_close with mixed positive/negative values."""
    assert not really_close(1000, -1000)
    assert not really_close(100, -100)


# Tests for assert_not_none function
def test_assert_not_none_with_value():
    """Test assert_not_none returns the value when not None."""
    result = assert_not_none(42)
    assert result == 42


def test_assert_not_none_with_string():
    """Test assert_not_none with string value."""
    result = assert_not_none("test")
    assert result == "test"


def test_assert_not_none_with_none():
    """Test assert_not_none raises AssertionError with None."""
    with pytest.raises(AssertionError):
        assert_not_none(None)


def test_assert_not_none_with_zero():
    """Test assert_not_none accepts zero."""
    result = assert_not_none(0)
    assert result == 0


def test_assert_not_none_with_false():
    """Test assert_not_none accepts False."""
    result = assert_not_none(False)
    assert result is False


def test_assert_not_none_with_empty_string():
    """Test assert_not_none accepts empty string."""
    result = assert_not_none("")
    assert result == ""


# Tests for c function (function composition)
def test_c_single_function():
    """Test composition with single function."""
    f = lambda x: x * 2
    composed = c(f)
    assert composed(5) == 10


def test_c_two_functions():
    """Test composition of two functions."""
    f = lambda x: x * 2
    g = lambda x: x + 3
    # c(g, f) means apply f first, then g to the result
    composed = c(g, f)
    assert composed(5) == (5 * 2) + 3  # = 13


def test_c_three_functions():
    """Test composition of three functions."""
    f = lambda x: x * 2
    g = lambda x: x + 3
    h = lambda x: x ** 2
    # c(h, g, f) applies f first, then g, then h
    composed = c(h, g, f)
    result = composed(2)  # f(2)=4, g(4)=7, h(7)=49
    assert result == 49


def test_c_with_string_transformation():
    """Test composition with string transformations."""
    to_upper = lambda x: x.upper()
    add_exclaim = lambda x: x + "!"
    composed = c(add_exclaim, to_upper)
    assert composed("hello") == "HELLO!"


# Tests for rc function (reverse composition - immediate application)
def test_rc_single_function():
    """Test reverse composition with single function."""
    f = lambda x: x * 2
    result = rc(f)(5)
    assert result == 10


def test_rc_multiple_functions():
    """Test reverse composition with multiple functions."""
    f = lambda x: x * 2
    g = lambda x: x + 3
    # rc applies the composition immediately
    result = rc(g, f)(5)
    assert result == (5 * 2) + 3


# Tests for subdates function
def test_subdates_naive_dates():
    """Test subdates with naive datetime objects."""
    d1 = datetime(2026, 4, 24, 10, 0, 0)
    d2 = datetime(2026, 4, 24, 9, 0, 0)
    delta = subdates(d1, d2)
    assert delta.total_seconds() == 3600  # 1 hour


def test_subdates_date_objects():
    """Test subdates with date objects."""
    d1 = date(2026, 4, 24)
    d2 = date(2026, 4, 23)
    delta = subdates(d1, d2)
    assert delta.days == 1


def test_subdates_timezone_aware():
    """Test subdates with timezone-aware datetimes."""
    tz = pytz.UTC
    d1 = tz.localize(datetime(2026, 4, 24, 10, 0, 0))
    d2 = tz.localize(datetime(2026, 4, 24, 9, 0, 0))
    delta = subdates(d1, d2)
    assert delta.total_seconds() == 3600


def test_subdates_mixed_timezone():
    """Test subdates with mixed timezone awareness."""
    tz = pytz.UTC
    d1 = tz.localize(datetime(2026, 4, 24, 10, 0, 0))  # Aware
    d2 = datetime(2026, 4, 24, 9, 0, 0)  # Naive - will be localized
    delta = subdates(d1, d2)
    assert delta.total_seconds() == 3600


# Tests for timeit decorator
def test_timeit_basic_function():
    """Test timeit decorator on basic function."""
    @timeit
    def slow_function():
        return 42

    result = slow_function()
    assert result == 42


def test_timeit_with_arguments():
    """Test timeit decorator with function arguments."""
    @timeit
    def add(a, b):
        return a + b

    result = add(3, 4)
    assert result == 7


def test_timeit_preserves_function_metadata():
    """Test that timeit preserves function name and docstring."""
    @timeit
    def my_function():
        """This is my function."""
        return 1

    assert my_function.__name__ == "my_function"
    assert my_function.__doc__ == "This is my function."


# Tests for localize_it function
def test_localize_it_naive_datetime():
    """Test localize_it with naive datetime."""
    dt = datetime(2026, 4, 24, 10, 0, 0)
    result = localize_it(dt)
    assert result.tzinfo is not None


def test_localize_it_aware_datetime():
    """Test localize_it with already-aware datetime."""
    tz = pytz.UTC
    dt = tz.localize(datetime(2026, 4, 24, 10, 0, 0))
    result = localize_it(dt)
    assert result.tzinfo is not None
    assert result == dt


def test_localize_it_date_object():
    """Test localize_it with date object (should return unchanged)."""
    d = date(2026, 4, 24)
    result = localize_it(d)
    assert result == d
    assert isinstance(result, date)


def test_localize_it_none():
    """Test localize_it with None (should return None)."""
    result = localize_it(None)
    assert result is None


# Tests for unlocalize_it function
def test_unlocalize_it_aware_datetime():
    """Test unlocalize_it with timezone-aware datetime."""
    tz = pytz.UTC
    dt = tz.localize(datetime(2026, 4, 24, 10, 0, 0))
    result = unlocalize_it(dt)
    assert result.tzinfo is None


def test_unlocalize_it_naive_datetime():
    """Test unlocalize_it with naive datetime."""
    dt = datetime(2026, 4, 24, 10, 0, 0)
    result = unlocalize_it(dt)
    assert result.tzinfo is None


def test_unlocalize_it_date_object():
    """Test unlocalize_it with date object (should return unchanged)."""
    d = date(2026, 4, 24)
    result = unlocalize_it(d)
    assert result == d
    assert isinstance(result, date)


def test_unlocalize_it_roundtrip():
    """Test localize_it followed by unlocalize_it."""
    dt = datetime(2026, 4, 24, 10, 0, 0)
    localized = localize_it(dt)
    unlocalized = unlocalize_it(localized)
    assert unlocalized.replace(tzinfo=None) == dt.replace(tzinfo=None)


# Tests for Types enum and bitflag operations
def test_types_enum_individual_flags():
    """Test individual Types flags."""
    assert Types.PRICE.value > 0
    assert Types.COMPARE.value > 0
    assert Types.VALUE.value > 0


def test_types_enum_combine_flags():
    """Test combining Types flags with | operator."""
    combined = Types.PRICE | Types.COMPARE
    assert combined != 0
    assert (combined & Types.PRICE) == Types.PRICE
    assert (combined & Types.COMPARE) == Types.COMPARE


def test_types_enum_check_flags():
    """Test checking combined flags with & operator."""
    combined = Types.PRICE | Types.COMPARE
    assert (combined & Types.PRICE) == Types.PRICE
    assert (combined & Types.VALUE) != Types.VALUE


def test_types_enum_predefined_combination():
    """Test predefined flag combination PRECDIFF."""
    # PRECDIFF = PRECENTAGE | DIFF
    assert (Types.PRECDIFF & Types.PRECENTAGE) == Types.PRECENTAGE
    assert (Types.PRECDIFF & Types.DIFF) == Types.DIFF


def test_types_enum_abs_flag():
    """Test ABS flag (should be 0)."""
    assert Types.ABS.value == 0


def test_types_enum_multiple_combinations():
    """Test multiple flag combinations."""
    f1 = Types.PRICE | Types.VALUE
    f2 = Types.PROFIT | Types.COMPARE
    combined = f1 | f2
    assert (combined & Types.PRICE) == Types.PRICE
    assert (combined & Types.VALUE) == Types.VALUE
    assert (combined & Types.PROFIT) == Types.PROFIT
    assert (combined & Types.COMPARE) == Types.COMPARE


# Tests for UniteType enum and bitflag operations
def test_unitetype_enum_individual_flags():
    """Test individual UniteType flags."""
    assert UniteType.SUM.value > 0
    assert UniteType.AVG.value > 0
    assert UniteType.MIN.value > 0
    assert UniteType.MAX.value > 0


def test_unitetype_enum_none_flag():
    """Test NONE flag (should be 0)."""
    assert UniteType.NONE.value == 0


def test_unitetype_enum_combine_flags():
    """Test combining UniteType flags."""
    combined = UniteType.SUM | UniteType.AVG
    assert (combined & UniteType.SUM) == UniteType.SUM
    assert (combined & UniteType.AVG) == UniteType.AVG


def test_unitetype_predefined_combination():
    """Test predefined UniteType combination ADDTOTALS."""
    # ADDTOTALS = ADDPROT | ADDTOTAL
    assert (UniteType.ADDTOTALS & UniteType.ADDPROT) == UniteType.ADDPROT
    assert (UniteType.ADDTOTALS & UniteType.ADDTOTAL) == UniteType.ADDTOTAL


def test_unitetype_enum_check_all_flags():
    """Test checking various UniteType flag combinations."""
    f = UniteType.SUM | UniteType.AVG | UniteType.MIN | UniteType.MAX
    assert (f & UniteType.SUM) == UniteType.SUM
    assert (f & UniteType.AVG) == UniteType.AVG
    assert (f & UniteType.MIN) == UniteType.MIN
    assert (f & UniteType.MAX) == UniteType.MAX


# Additional integration tests
def test_tzawareness_with_aware_date():
    """Test tzawareness function with timezone-aware date."""
    tz = pytz.UTC
    d1 = datetime(2026, 4, 24, 10, 0, 0)
    d2 = tz.localize(datetime(2026, 4, 24, 9, 0, 0))
    result = tzawareness(d1, d2)
    assert result.tzinfo is not None


def test_tzawareness_with_naive_date():
    """Test tzawareness function with naive reference date."""
    d1 = datetime(2026, 4, 24, 10, 0, 0)
    d2 = datetime(2026, 4, 24, 9, 0, 0)
    result = tzawareness(d1, d2)
    assert result.tzinfo is None


def test_composition_with_localize():
    """Test composition functions work with localize_it."""
    f = localize_it
    g = lambda x: x.replace(hour=12) if x is not None else None
    composed = c(g, f)
    dt = datetime(2026, 4, 24, 10, 0, 0)
    result = composed(dt)
    assert result.hour == 12
    assert result.tzinfo is not None
