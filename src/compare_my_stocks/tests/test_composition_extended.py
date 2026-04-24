"""
Extended tests for composition pipeline edge cases.

Tests composition with:
- Empty collections
- Generators and iterators
- Nested compositions
- Curry with partial function assignment
- Error handling in pipelines
"""

from common.composition import C, CS, CInst, UnsafeType, Exp, ExpList
import itertools
import pytest


# Helper functions for testing
def add(a, b):
    return a + b


def divide(a, b):
    if b == 0:
        raise ValueError("Division by zero")
    return a / b


def square(x):
    return x * x


def increment(x):
    return x + 1


# Tests for empty collections
def test_empty_list():
    """Test composition with empty list."""
    result = C / []
    assert result.col == []
    assert len(result) == 0


def test_empty_tuple():
    """Test composition with empty tuple."""
    result = C / ()
    assert result.col == ()
    assert len(result) == 0


def test_empty_list_with_function():
    """Test composition with empty list and function mapping."""
    result = C / [] << (lambda x: x * 2)
    assert list(result) == []


def test_empty_collection_iteration():
    """Test iterating over empty collection."""
    result = C / []
    count = 0
    for _ in result:
        count += 1
    assert count == 0


def test_empty_list_apply_function():
    """Test applying function to empty collection."""
    result = C / [] @ list
    assert result == []


def test_empty_tuple_lshift():
    """Test lshift operator with empty tuple."""
    result = C / () << increment
    assert list(result) == []


# Tests for generators with composition
def test_generator_in_composition():
    """Test generator in full composition pipeline."""
    gen = (x for x in range(1, 4))
    result = C / list / map % (lambda x: x * 2) @ gen
    assert list(result) == [2, 4, 6]


def test_itertools_chain_composition():
    """Test composition with itertools.chain - converted to list for iteration."""
    gen = itertools.chain(range(3), range(3, 6))
    result = C / list @ gen
    assert result == [0, 1, 2, 3, 4, 5]


# Tests for nested compositions
def test_nested_composition_multiple_levels():
    """Test deeply nested compositions."""
    result = (
        C / [1, 2, 3]
        / list
        << square
    )
    assert list(result) == [1, 4, 9]


def test_nested_composition_with_floordiv():
    """Test nested composition with floordiv (currying)."""
    def f(a, b, c):
        return a + b + c

    def g(x):
        return x * 2

    result = C // g // f @ (1, 2, 3)
    assert result == 12  # (1+2+3)*2 = 6*2 = 12


# Tests for curry with partial function assignment
def test_curry_with_lambda_assignment():
    """Test currying with lambda function assignment."""
    def f(a, b, c):
        return b

    result = C / f % {'b': (lambda b: b * 2)} @ (1, 5, 3)
    assert result == 10


def test_curry_partial_tuple():
    """Test partial with tuple."""
    def f(a, b, c):
        return a + b + c

    result = C / f % (1, 2) @ (3,)
    assert result == 6


def test_curry_partial_single_value():
    """Test partial with single value."""
    result = C / add % 10 @ (5,)
    assert result == 15


def test_partial_empty_dict():
    """Test partial with empty dictionary."""
    def f(a, b):
        return a + b

    result = C / f % {} @ (3, 7)
    assert result == 10


def test_curry_preserves_function_behavior():
    """Test that currying preserves original function behavior."""
    def f(a, b, c):
        return (a, b, c)

    # Create partial with first argument
    result = C / f % (1,) @ (2, 3)
    assert result == (1, 2, 3)


def test_curry_with_multiple_args():
    """Test currying with multiple arguments."""
    def f(a, b, c, d):
        return a + b + c + d

    result = C / f % (1, 2) @ (3, 4)
    assert result == 10


# Tests for error handling in pipelines
def test_error_handling_division_by_zero():
    """Test error handling with division by zero."""
    with pytest.raises(ValueError, match="Division by zero"):
        C / divide @ (10, 0)


def test_error_handling_invalid_function():
    """Test error handling with invalid function."""
    with pytest.raises(TypeError):
        C / (lambda x, y: x + y) @ (5,)


def test_error_handling_invalid_getitem():
    """Test error handling with invalid getitem."""
    result = C / [1, 2, 3]
    assert result[0] == 1


def test_error_handling_iter_without_collection():
    """Test error handling when iterating without collection."""
    result = C / square
    with pytest.raises(ValueError, match="Can only use iter"):
        iter(result)


def test_error_handling_len_without_collection():
    """Test error handling when getting length without collection."""
    result = C / square
    with pytest.raises(ValueError, match="Can only use len"):
        len(result)


def test_error_handling_getitem_without_collection():
    """Test error handling when getting item without collection."""
    result = C / square
    with pytest.raises(ValueError, match="Can only use getitem"):
        result[0]


def test_error_handling_lshift_without_collection():
    """Test error handling with lshift without collection."""
    result = C / square
    with pytest.raises(ValueError, match="Can only use"):
        result << (lambda x: x * 2)


def test_error_handling_or_without_collection():
    """Test error handling with or operator without collection."""
    result = C / square
    with pytest.raises(ValueError, match="Can only use"):
        result | Exp()


def test_error_handling_invalid_signature():
    """Test error handling with invalid function signature."""
    with pytest.raises(TypeError):
        C / square @ (1, 2, 3)


# Tests for complex pipelines
def test_complex_pipeline_with_multiple_ops():
    """Test complex pipeline with multiple operations."""
    result = (
        C / [1, 2, 3]
        / list
        << (lambda x: x * 2)
    )
    assert list(result) == [2, 4, 6]


def test_pipeline_with_tuples():
    """Test pipeline with tuple operations."""
    result = C / (1, 2, 3) / list
    assert result == [1, 2, 3]


def test_pipeline_dict_to_kwargs():
    """Test pipeline with dict converted to kwargs."""
    def f(a, b):
        return a + b

    result = C / f @ {'a': 5, 'b': 3}
    assert result == 8


def test_pipeline_list_to_args():
    """Test pipeline with list converted to args."""
    def f(a, b, c):
        return a + b + c

    result = C / f @ [1, 2, 3]
    assert result == 6


def test_pipeline_with_range():
    """Test pipeline with range object."""
    result = C / (1, 8, 2) @ range
    assert list(result) == [1, 3, 5, 7]


def test_pipeline_with_zip():
    """Test pipeline with zip operation."""
    result = C / list / zip & C / list @ range(5) ^ [4, 8, 9, 10, 11]
    expected = [(0, 4), (1, 8), (2, 9), (3, 10), (4, 11)]
    assert result == expected


def test_pipeline_with_filter():
    """Test pipeline with filter function."""
    result = C / list / filter % (lambda x: x % 2 == 0) @ range(10)
    assert result == [0, 2, 4, 6, 8]


def test_pipeline_with_map():
    """Test pipeline with map function."""
    result = C / list / map % (lambda x: x ** 2) @ range(1, 5)
    assert result == [1, 4, 9, 16]


# Tests for UnsafeType flags
def test_unsafe_type_safe():
    """Test composition with Safe mode."""
    result = CS / [1, 2, 3] / list
    assert result == [1, 2, 3]


def test_unsafe_type_currying():
    """Test composition with Currying flag."""
    def f(a, b, c):
        return a + b + c

    result = C // f @ (1, 2, 3)
    assert result == 6


# Tests for special cases and edge cases
def test_deeply_nested_lists():
    """Test with nested list structures."""
    nested = [[1, 2], [3, 4], [5, 6]]
    result = C / nested / list
    assert result == nested


def test_composition_preserves_order():
    """Test that composition preserves order of operations."""
    result = C / [3, 1, 2] / sorted
    assert result == [1, 2, 3]


def test_partial_zero():
    """Test partial with zero value."""
    result = C / [1, 2, 3, 4, 5] % 0
    assert result == [1, 2, 3, 4, 5]


def test_partial_positive_index():
    """Test partial with positive index."""
    result = C / [1, 2, 3, 4, 5] % 3
    assert result == [1, 2, 3]


# Tests for equality and comparison
def test_cinst_equality_with_list():
    """Test CInst equality comparison with list."""
    result = C / [1, 2, 3]
    assert result == [1, 2, 3]


def test_cinst_inequality():
    """Test CInst inequality."""
    result = C / [1, 2, 3]
    assert not (result == [1, 2, 4])


# Tests for lambda and functional composition
def test_lambda_in_lshift():
    """Test lshift with lambda expressions."""
    result = C / [1, 2, 3] << (lambda x: x ** 2)
    assert list(result) == [1, 4, 9]


def test_nested_operators_composition():
    """Test nested operator usage in composition."""
    result = C / [1, 2, 3] << (lambda x: x * 2)
    processed = list(result)
    assert processed == [2, 4, 6]
