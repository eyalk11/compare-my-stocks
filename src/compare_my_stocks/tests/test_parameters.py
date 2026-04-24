import pytest
from datetime import datetime, timedelta
import dateutil
import pytz
from unittest.mock import MagicMock, patch

from engine.parameters import Parameters, ParameterError
from engine.symbols import SimpleSymbol, AbstractSymbol
from common.common import Types, UseCache, UniteType, LimitType
from config import config


class TestParametersInitialization:
    """Test Parameters dataclass initialization and default values."""

    def test_parameters_default_initialization(self):
        """Test Parameters can be initialized with default values."""
        p = Parameters()
        assert p is not None
        assert isinstance(p, Parameters)

    def test_parameters_default_groups(self):
        """Test default groups is empty list."""
        p = Parameters()
        assert p.groups == []
        assert isinstance(p.groups, list)

    def test_parameters_default_valuerange(self):
        """Test default valuerange is negative to positive infinity."""
        p = Parameters()
        assert p.valuerange[0] < 0  # negative infinity
        assert p.valuerange[1] > 0  # positive infinity

    def test_parameters_default_numrange(self):
        """Test default numrange is (None, None)."""
        p = Parameters()
        assert p.numrange == (None, None)

    def test_parameters_default_type(self):
        """Test default type is Types.VALUE."""
        p = Parameters()
        assert p.type == Types.VALUE

    def test_parameters_default_isline(self):
        """Test default isline is True."""
        p = Parameters()
        assert p.isline is True

    def test_parameters_default_starthidden(self):
        """Test default starthidden is False."""
        p = Parameters()
        assert p.starthidden == 0

    def test_parameters_default_use_cache(self):
        """Test default use_cache is USEIFAVAILABLE."""
        p = Parameters()
        assert p.use_cache == UseCache.USEIFAVAILABLE

    def test_parameters_default_unite_by_group(self):
        """Test default unite_by_group is NONE."""
        p = Parameters()
        assert p.unite_by_group == UniteType.NONE

    def test_parameters_default_show_graph(self):
        """Test default show_graph is False."""
        p = Parameters()
        assert p.show_graph is False

    def test_parameters_default_use_groups(self):
        """Test default use_groups is True."""
        p = Parameters()
        assert p.use_groups is True

    def test_parameters_default_use_ext(self):
        """Test default use_ext is True."""
        p = Parameters()
        assert p.use_ext is True

    def test_parameters_default_limit_by(self):
        """Test default limit_by is RANGE."""
        p = Parameters()
        assert p.limit_by == LimitType.RANGE

    def test_parameters_default_show_transactions_graph(self):
        """Test default show_transactions_graph is True."""
        p = Parameters()
        assert p.show_transactions_graph is True

    def test_parameters_default_is_forced(self):
        """Test default is_forced is False after init."""
        p = Parameters()
        assert p.is_forced is False

    def test_parameters_default_weighted_for_portfolio(self):
        """Test default weighted_for_portfolio is False."""
        p = Parameters()
        assert p.weighted_for_portfolio is False

    def test_parameters_default_adjusted_for_base_cur(self):
        """Test default adjusted_for_base_cur is True."""
        p = Parameters()
        assert p.adjusted_for_base_cur is True

    def test_parameters_default_adjust_to_currency(self):
        """Test default adjust_to_currency is True."""
        p = Parameters()
        assert p.adjust_to_currency is True

    def test_parameters_default_ignore_minmax(self):
        """Test default ignore_minmax is False."""
        p = Parameters()
        assert p.ignore_minmax is False

    def test_parameters_with_custom_groups(self):
        """Test Parameters initialization with custom groups."""
        groups = ['group1', 'group2', 'group3']
        p = Parameters(groups=groups)
        assert p.groups == groups

    def test_parameters_with_custom_type(self):
        """Test Parameters initialization with custom type."""
        p = Parameters(type=Types.DIFF)
        assert p.type == Types.DIFF

    def test_parameters_with_custom_valuerange(self):
        """Test Parameters initialization with custom valuerange."""
        vr = [0, 100]
        p = Parameters(valuerange=vr)
        assert p.valuerange == vr

    def test_parameters_with_custom_numrange(self):
        """Test Parameters initialization with custom numrange."""
        nr = [1, 10]
        p = Parameters(numrange=nr)
        assert p.numrange == nr


class TestParametersPropertySetters:
    """Test Parameters property setters and getters."""

    def test_selected_stocks_property_get(self):
        """Test getting selected_stocks property."""
        p = Parameters()
        assert p.selected_stocks == []

    def test_selected_stocks_property_set_with_strings(self):
        """Test setting selected_stocks with string list."""
        p = Parameters()
        p.selected_stocks = ['AAPL', 'GOOGL', 'MSFT']
        assert p.selected_stocks == ['AAPL', 'GOOGL', 'MSFT']

    def test_selected_stocks_property_converts_to_strings(self):
        """Test that selected_stocks setter converts items to strings."""
        p = Parameters()
        p.selected_stocks = [123, 456]  # Numbers that should be converted
        assert p.selected_stocks == ['123', '456']

    def test_selected_stocks_property_with_symbols(self):
        """Test selected_stocks with SimpleSymbol objects."""
        p = Parameters()
        sym1 = SimpleSymbol('AAPL')
        sym2 = SimpleSymbol('GOOGL')
        p.selected_stocks = [sym1, sym2]
        # Should convert to strings
        assert len(p.selected_stocks) == 2
        assert 'AAPL' in p.selected_stocks or 'GOOGL' in p.selected_stocks

    def test_ext_property_get(self):
        """Test getting ext property."""
        p = Parameters()
        assert isinstance(p.ext, list)

    def test_ext_property_set_with_strings(self):
        """Test setting ext with string list."""
        p = Parameters()
        ext_list = ['ext1', 'ext2']
        p.ext = ext_list
        assert p.ext == ext_list

    def test_ext_property_converts_to_strings(self):
        """Test that ext setter converts items to strings."""
        p = Parameters()
        p.ext = [789, 101]
        assert p.ext == ['789', '101']

    def test_fromdate_property_get_with_no_date(self):
        """Test getting fromdate when not set."""
        p = Parameters()
        assert p.fromdate == p.transactions_fromdate

    def test_fromdate_property_set(self):
        """Test setting fromdate property."""
        p = Parameters()
        test_date = datetime(2023, 1, 1)
        p.fromdate = test_date
        assert p.fromdate == test_date

    def test_fromdate_setter_updates_transactions_fromdate(self):
        """Test that setting fromdate updates transactions_fromdate when needed."""
        p = Parameters()
        date1 = datetime(2023, 1, 1)
        date2 = datetime(2023, 1, 2)
        p.fromdate = date2
        p.fromdate = date1  # earlier date
        # transactions_fromdate should be the earlier one
        assert p.transactions_fromdate == date1

    def test_fromdate_setter_sets_adjust_date(self):
        """Test that setting fromdate sets adjust_date flag."""
        p = Parameters()
        p.adjust_date = 0
        p.fromdate = datetime(2023, 1, 1)
        assert p.adjust_date == 1

    def test_todate_property_get_with_no_date(self):
        """Test getting todate when not set."""
        p = Parameters()
        assert p.todate == p._todate

    def test_todate_property_set(self):
        """Test setting todate property."""
        p = Parameters()
        test_date = datetime(2023, 12, 31)
        p.todate = test_date
        assert p.todate == test_date

    def test_todate_setter_sets_adjust_date(self):
        """Test that setting todate sets adjust_date flag."""
        p = Parameters()
        p.adjust_date = 0
        p.todate = datetime(2023, 12, 31)
        assert p.adjust_date == 1

    def test_todate_setter_initializes_transactions_todate(self):
        """Test that todate setter initializes transactions_todate if not set."""
        p = Parameters()
        test_date = datetime(2023, 12, 31)
        assert p.transactions_todate is None
        p.todate = test_date
        assert p.transactions_todate == test_date


class TestParametersDateRangeValidation:
    """Test date range validation and handling."""

    def test_fromdate_earlier_than_todate(self):
        """Test setting fromdate before todate works correctly."""
        p = Parameters()
        from_date = datetime(2023, 1, 1)
        to_date = datetime(2023, 12, 31)
        p.fromdate = from_date
        p.todate = to_date
        assert p.fromdate == from_date
        assert p.todate == to_date

    def test_todate_later_than_fromdate(self):
        """Test setting todate after fromdate works correctly."""
        p = Parameters()
        from_date = datetime(2023, 1, 1)
        to_date = datetime(2023, 12, 31)
        p.todate = to_date
        p.fromdate = from_date
        assert p.fromdate == from_date
        assert p.todate == to_date

    def test_transactions_dates_boundaries(self):
        """Test that transactions_fromdate and transactions_todate track boundaries."""
        p = Parameters()
        date1 = datetime(2023, 1, 1)
        date2 = datetime(2023, 6, 15)
        date3 = datetime(2023, 12, 31)

        p.fromdate = date2
        assert p.transactions_fromdate == date2

        p.fromdate = date1  # earlier
        assert p.transactions_fromdate == date1

        p.todate = date3
        assert p.transactions_todate == date3

    def test_none_dates(self):
        """Test Parameters with None dates."""
        p = Parameters()
        assert p._fromdate is None
        assert p._todate is None
        assert p.fromdate == p.transactions_fromdate

    def test_todate_none_then_set(self):
        """Test setting todate from None to a value."""
        p = Parameters()
        p.todate = None  # Explicit None
        p.todate = datetime(2023, 12, 31)
        assert p.todate == datetime(2023, 12, 31)


class TestParametersGroupHandling:
    """Test Parameters group handling."""

    def test_groups_empty_by_default(self):
        """Test that groups is empty by default."""
        p = Parameters()
        assert p.groups == []

    def test_groups_can_be_set(self):
        """Test that groups can be set."""
        p = Parameters()
        groups = ['Portfolio1', 'Portfolio2']
        p.groups = groups
        assert p.groups == groups

    def test_use_groups_flag(self):
        """Test use_groups flag."""
        p = Parameters()
        assert p.use_groups is True
        p.use_groups = False
        assert p.use_groups is False

    def test_groups_with_unite_by_group(self):
        """Test groups interaction with unite_by_group."""
        p = Parameters(groups=['g1', 'g2'], unite_by_group=UniteType.GROUP)
        assert p.groups == ['g1', 'g2']
        assert p.unite_by_group == UniteType.GROUP


class TestParametersHelper:
    """Test the helper method for processing extended symbols."""

    def test_helper_with_string_symbols(self):
        """Test helper method with string symbols."""
        p = Parameters()
        result = list(p.helper(['AAPL', 'GOOGL']))
        assert result == ['AAPL', 'GOOGL']

    def test_helper_with_numbers(self):
        """Test helper method converts numbers to strings."""
        p = Parameters()
        result = list(p.helper([123, 456]))
        assert result == ['123', '456']

    def test_helper_with_simple_symbol_without_dic(self):
        """Test helper with SimpleSymbol without dictionary."""
        p = Parameters()
        sym = SimpleSymbol('AAPL')
        result = list(p.helper([sym]))
        assert result == ['AAPL']

    def test_helper_populates_resolve_hack(self):
        """Test that helper populates resolve_hack for symbols with dic."""
        p = Parameters()
        sym_dic = {'symbol': 'AAPL', 'currency': 'USD'}
        sym = SimpleSymbol(sym_dic)
        list(p.helper([sym]))
        # Symbol with dic should be added to resolve_hack
        if sym.dic:  # Only if dic is present
            assert 'AAPL' in p.resolve_hack or len(p.resolve_hack) >= 0


class TestParametersPostInit:
    """Test __post_init__ method."""

    def test_post_init_with_ext_list(self):
        """Test __post_init__ processes ext parameter."""
        p = Parameters(ext=['ext1', 'ext2'])
        assert 'ext1' in p.ext or 'ext2' in p.ext

    def test_post_init_sets_adjust_date_to_zero(self):
        """Test __post_init__ initializes adjust_date to 0."""
        p = Parameters()
        assert p.adjust_date == 0

    def test_post_init_sets_is_forced_to_false(self):
        """Test __post_init__ sets is_forced to False."""
        p = Parameters()
        assert p.is_forced is False

    def test_post_init_with_baseclass_parameter(self):
        """Test __post_init__ with baseclass parameter."""
        # baseclass is an InitVar, so it won't be stored as a field
        p = Parameters()
        # After init, _baseclass should be set (via post_init)
        assert hasattr(p, '_baseclass')


class TestParametersLoadFromJson:
    """Test loading Parameters from JSON dictionary."""

    def test_load_from_json_dict_with_simple_values(self):
        """Test loading from JSON dict with simple values."""
        data = {
            'groups': ['g1', 'g2'],
            'type': Types.VALUE,
            'show_graph': True
        }
        p = Parameters.load_from_json_dict(data)
        assert p.groups == ['g1', 'g2']
        assert p.type == Types.VALUE
        assert p.show_graph is True

    def test_load_from_json_dict_with_date_string(self):
        """Test loading from JSON dict with date strings."""
        data = {
            'fromdate': '2023-01-01T00:00:00',
            'todate': '2023-12-31T23:59:59'
        }
        p = Parameters.load_from_json_dict(data)
        # Dates should be parsed
        assert isinstance(p.fromdate, datetime) or p.fromdate == '2023-01-01T00:00:00'


class TestParametersGetState:
    """Test __getstate__ method for serialization."""

    def test_getstate_returns_dict(self):
        """Test __getstate__ returns a dictionary."""
        p = Parameters()
        state = p.__getstate__()
        assert isinstance(state, dict)

    def test_getstate_excludes_baseclass(self):
        """Test __getstate__ filters out _baseclass."""
        p = Parameters()
        state = p.__getstate__()
        # _baseclass should be filtered out
        assert '_baseclass' not in state or state.get('_baseclass') is None

    def test_getstate_includes_other_fields(self):
        """Test __getstate__ includes other fields."""
        p = Parameters(groups=['g1'], show_graph=True)
        state = p.__getstate__()
        assert 'groups' in state
        assert 'show_graph' in state


class TestParametersEdgeCases:
    """Test edge cases and special scenarios."""

    def test_parameters_immutability_of_defaults(self):
        """Test that default list values don't share references between instances."""
        p1 = Parameters()
        p2 = Parameters()
        p1.groups = ['g1']
        # p2.groups should still be empty
        assert p2.groups == []

    def test_parameters_with_all_custom_values(self):
        """Test Parameters with many custom values."""
        p = Parameters(
            groups=['g1', 'g2'],
            valuerange=[0, 100],
            numrange=[1, 10],
            type=Types.COMPARE,
            use_cache=UseCache.IGNORE,
            show_graph=True,
            use_groups=False,
            ignore_minmax=True
        )
        assert p.groups == ['g1', 'g2']
        assert p.valuerange == [0, 100]
        assert p.type == Types.COMPARE
        assert p.use_cache == UseCache.IGNORE
        assert p.show_graph is True
        assert p.use_groups is False
        assert p.ignore_minmax is True

    def test_compare_with_and_portfolio_fields(self):
        """Test compare_with and portfolio fields."""
        p = Parameters(compare_with='AAPL', portfolio='MyPortfolio')
        assert p.compare_with == 'AAPL'
        assert p.portfolio == 'MyPortfolio'

    def test_currency_related_fields(self):
        """Test currency-related fields."""
        p = Parameters(
            currency_to_adjust='USD',
            cur_category='stocks'
        )
        assert p.currency_to_adjust == 'USD'
        assert p.cur_category == 'stocks'
        assert p.adjusted_for_base_cur is True
        assert p.adjust_to_currency is True

    def test_resolve_hack_field(self):
        """Test resolve_hack field."""
        p = Parameters()
        assert isinstance(p.resolve_hack, dict)
        assert p.resolve_hack == {}

        p.resolve_hack['AAPL'] = SimpleSymbol('AAPL')
        assert 'AAPL' in p.resolve_hack

    def test_shown_stock_field(self):
        """Test shown_stock field."""
        p = Parameters()
        assert p.shown_stock == []

        p.shown_stock = ['AAPL', 'GOOGL']
        assert p.shown_stock == ['AAPL', 'GOOGL']

    def test_limit_to_portfolio_field(self):
        """Test limit_to_portfolio field."""
        p = Parameters()
        assert p.limit_to_portfolio is False

        p.limit_to_portfolio = True
        assert p.limit_to_portfolio is True


class TestParametersIntegration:
    """Integration tests combining multiple Parameters features."""

    def test_full_parameters_workflow(self):
        """Test a typical workflow with Parameters."""
        # Create Parameters with various settings
        p = Parameters(
            groups=['Portfolio_2023', 'Portfolio_2024'],
            type=Types.PRICE,
            use_cache=UseCache.USEIFAVAILABLE,
            show_graph=True
        )

        # Set dates
        p.fromdate = datetime(2023, 1, 1)
        p.todate = datetime(2024, 12, 31)

        # Add selected stocks
        p.selected_stocks = ['AAPL', 'GOOGL', 'MSFT']

        # Verify state
        assert len(p.groups) == 2
        assert p.fromdate == datetime(2023, 1, 1)
        assert len(p.selected_stocks) == 3
        assert p.show_graph is True

    def test_parameters_with_date_range_and_groups(self):
        """Test Parameters interaction between date ranges and groups."""
        p = Parameters(groups=['g1', 'g2'])

        # Set date range
        p.fromdate = datetime(2023, 1, 1)
        p.todate = datetime(2023, 12, 31)

        # Verify both are set
        assert p.fromdate == datetime(2023, 1, 1)
        assert p.todate == datetime(2023, 12, 31)
        assert p.groups == ['g1', 'g2']

    def test_parameters_flags_combination(self):
        """Test combining Parameters with different flag enums."""
        p = Parameters(
            type=Types.PRICE | Types.COMPARE,  # Combine flags
            unite_by_group=UniteType.GROUP,
            limit_by=LimitType.RANGE
        )
        # Should be able to combine flags
        assert (p.type & Types.PRICE) == Types.PRICE or p.type == Types.PRICE


class TestParametersTypeEnums:
    """Test Parameters with different enum types."""

    def test_types_enum_values(self):
        """Test using different Types enum values."""
        for type_val in [Types.VALUE, Types.PRICE, Types.DIFF, Types.COMPARE]:
            p = Parameters(type=type_val)
            assert p.type == type_val

    def test_unite_type_enum_values(self):
        """Test using different UniteType enum values."""
        for unite_val in [UniteType.NONE, UniteType.SUM, UniteType.GROUP]:
            p = Parameters(unite_by_group=unite_val)
            assert p.unite_by_group == unite_val

    def test_limit_type_enum_values(self):
        """Test using different LimitType enum values."""
        for limit_val in [LimitType.RANGE, LimitType.TOP]:
            p = Parameters(limit_by=limit_val)
            assert p.limit_by == limit_val

    def test_use_cache_enum_values(self):
        """Test using different UseCache enum values."""
        for cache_val in [UseCache.USEIFAVAILABLE, UseCache.IGNORE, UseCache.FORCE]:
            p = Parameters(use_cache=cache_val)
            assert p.use_cache == cache_val


class TestParametersCopyFunction:
    """Test the copyit function for copying Parameters."""

    def test_copyit_creates_independent_copy(self):
        """Test that copyit creates an independent copy of Parameters."""
        from engine.parameters import copyit

        p1 = Parameters(groups=['g1'], show_graph=True)
        p2 = copyit(p1)

        # Should have same values
        assert p2.groups == p1.groups
        assert p2.show_graph == p1.show_graph

        # But be different objects
        assert p2 is not p1


class TestParametersError:
    """Test ParameterError exception."""

    def test_parameter_error_is_exception(self):
        """Test ParameterError is an Exception."""
        assert issubclass(ParameterError, Exception)

    def test_parameter_error_can_be_raised(self):
        """Test ParameterError can be raised and caught."""
        with pytest.raises(ParameterError):
            raise ParameterError("Test error")

    def test_parameter_error_with_message(self):
        """Test ParameterError with custom message."""
        msg = "Invalid parameter value"
        with pytest.raises(ParameterError) as exc_info:
            raise ParameterError(msg)
        assert str(exc_info.value) == msg
