#!/usr/bin/env python
"""Manual test runner for test_common.py"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Try to run tests manually
test_results = []

# Test really_close function
print("=" * 70)
print("Testing really_close function")
print("=" * 70)

from common.common import really_close

tests = [
    ("test_really_close_equal_values", lambda: really_close(10, 10) == True),
    ("test_really_close_with_tolerance", lambda: really_close(1000, 1000.5) and really_close(1000, 999.5)),
    ("test_really_close_beyond_tolerance", lambda: not really_close(1000, 998)),
    ("test_really_close_zero_handling", lambda: really_close(0, 0) and really_close(0, 0.0005) and not really_close(0, 0.002)),
    ("test_really_close_negative_values", lambda: really_close(-1000, -1000.5) and really_close(-1000, -999.5)),
]

for test_name, test_func in tests:
    try:
        result = test_func()
        if result:
            print(f"✓ PASSED: {test_name}")
            test_results.append((test_name, "PASSED"))
        else:
            print(f"✗ FAILED: {test_name}")
            test_results.append((test_name, "FAILED"))
    except Exception as e:
        print(f"✗ ERROR: {test_name} - {e}")
        test_results.append((test_name, f"ERROR: {e}"))

# Test assert_not_none function
print("\n" + "=" * 70)
print("Testing assert_not_none function")
print("=" * 70)

from common.common import assert_not_none

tests = [
    ("test_assert_not_none_with_value", lambda: assert_not_none(42) == 42),
    ("test_assert_not_none_with_string", lambda: assert_not_none("test") == "test"),
    ("test_assert_not_none_with_zero", lambda: assert_not_none(0) == 0),
    ("test_assert_not_none_with_false", lambda: assert_not_none(False) is False),
    ("test_assert_not_none_with_empty_string", lambda: assert_not_none("") == ""),
]

for test_name, test_func in tests:
    try:
        result = test_func()
        if result:
            print(f"✓ PASSED: {test_name}")
            test_results.append((test_name, "PASSED"))
        else:
            print(f"✗ FAILED: {test_name}")
            test_results.append((test_name, "FAILED"))
    except Exception as e:
        print(f"✗ ERROR: {test_name} - {e}")
        test_results.append((test_name, f"ERROR: {e}"))

# Test assert_not_none with None (should raise)
print("\nTesting assert_not_none with None (should raise AssertionError):")
try:
    assert_not_none(None)
    print(f"✗ FAILED: test_assert_not_none_with_none - Should have raised AssertionError")
    test_results.append(("test_assert_not_none_with_none", "FAILED"))
except AssertionError:
    print(f"✓ PASSED: test_assert_not_none_with_none")
    test_results.append(("test_assert_not_none_with_none", "PASSED"))

# Test c function (composition)
print("\n" + "=" * 70)
print("Testing c function (function composition)")
print("=" * 70)

from common.common import c

tests = [
    ("test_c_single_function", lambda: c(lambda x: x * 2)(5) == 10),
    ("test_c_two_functions", lambda: c(lambda x: x + 3, lambda x: x * 2)(5) == 13),
    ("test_c_three_functions", lambda: c(lambda x: x ** 2, lambda x: x + 3, lambda x: x * 2)(2) == 49),
]

for test_name, test_func in tests:
    try:
        result = test_func()
        if result:
            print(f"✓ PASSED: {test_name}")
            test_results.append((test_name, "PASSED"))
        else:
            print(f"✗ FAILED: {test_name}")
            test_results.append((test_name, "FAILED"))
    except Exception as e:
        print(f"✗ ERROR: {test_name} - {e}")
        test_results.append((test_name, f"ERROR: {e}"))

# Test rc function
print("\n" + "=" * 70)
print("Testing rc function (reverse composition)")
print("=" * 70)

from common.common import rc

tests = [
    ("test_rc_single_function", lambda: rc(lambda x: x * 2)(5) == 10),
    ("test_rc_multiple_functions", lambda: rc(lambda x: x + 3, lambda x: x * 2)(5) == 13),
]

for test_name, test_func in tests:
    try:
        result = test_func()
        if result:
            print(f"✓ PASSED: {test_name}")
            test_results.append((test_name, "PASSED"))
        else:
            print(f"✗ FAILED: {test_name}")
            test_results.append((test_name, "FAILED"))
    except Exception as e:
        print(f"✗ ERROR: {test_name} - {e}")
        test_results.append((test_name, f"ERROR: {e}"))

# Test subdates function
print("\n" + "=" * 70)
print("Testing subdates function")
print("=" * 70)

from common.common import subdates
from datetime import datetime, date

tests = [
    ("test_subdates_naive_dates", lambda: subdates(
        datetime(2026, 4, 24, 10, 0, 0),
        datetime(2026, 4, 24, 9, 0, 0)
    ).total_seconds() == 3600),
    ("test_subdates_date_objects", lambda: subdates(
        date(2026, 4, 24),
        date(2026, 4, 23)
    ).days == 1),
]

for test_name, test_func in tests:
    try:
        result = test_func()
        if result:
            print(f"✓ PASSED: {test_name}")
            test_results.append((test_name, "PASSED"))
        else:
            print(f"✗ FAILED: {test_name}")
            test_results.append((test_name, "FAILED"))
    except Exception as e:
        print(f"✗ ERROR: {test_name} - {e}")
        test_results.append((test_name, f"ERROR: {e}"))

# Test timeit decorator
print("\n" + "=" * 70)
print("Testing timeit decorator")
print("=" * 70)

from common.common import timeit

tests_timeit = [
    ("test_timeit_basic_function", lambda: (lambda: (
        f := (lambda: 42),
        result := (lambda: f())(),
        result == 42
    ))()[-1]),
    ("test_timeit_preserves_name", lambda: (
        (lambda f: f.__name__ == "my_function")(
            (lambda: (
                f := lambda: 1,
                setattr(f, '__name__', 'my_function'),
                f
            )()[-1])()
        )
    )),
]

# Simpler timeit test
@timeit
def slow_function():
    return 42

result = slow_function()
if result == 42:
    print(f"✓ PASSED: test_timeit_basic_function")
    test_results.append(("test_timeit_basic_function", "PASSED"))
else:
    print(f"✗ FAILED: test_timeit_basic_function")
    test_results.append(("test_timeit_basic_function", "FAILED"))

# Test localize_it and unlocalize_it
print("\n" + "=" * 70)
print("Testing localize_it and unlocalize_it functions")
print("=" * 70)

from common.common import localize_it, unlocalize_it
import pytz

tests = [
    ("test_localize_it_naive_datetime", lambda: localize_it(datetime(2026, 4, 24, 10, 0, 0)).tzinfo is not None),
    ("test_localize_it_date_object", lambda: localize_it(date(2026, 4, 24)) == date(2026, 4, 24)),
    ("test_localize_it_none", lambda: localize_it(None) is None),
    ("test_unlocalize_it_aware_datetime", lambda: unlocalize_it(
        pytz.UTC.localize(datetime(2026, 4, 24, 10, 0, 0))
    ).tzinfo is None),
    ("test_unlocalize_it_date_object", lambda: unlocalize_it(date(2026, 4, 24)) == date(2026, 4, 24)),
]

for test_name, test_func in tests:
    try:
        result = test_func()
        if result:
            print(f"✓ PASSED: {test_name}")
            test_results.append((test_name, "PASSED"))
        else:
            print(f"✗ FAILED: {test_name}")
            test_results.append((test_name, "FAILED"))
    except Exception as e:
        print(f"✗ ERROR: {test_name} - {e}")
        test_results.append((test_name, f"ERROR: {e}"))

# Test Types enum with bitflags
print("\n" + "=" * 70)
print("Testing Types enum and bitflag operations")
print("=" * 70)

from common.common import Types

tests = [
    ("test_types_enum_individual_flags", lambda: Types.PRICE.value > 0 and Types.COMPARE.value > 0),
    ("test_types_enum_combine_flags", lambda: (Types.PRICE | Types.COMPARE) != 0),
    ("test_types_enum_check_flags", lambda: (
        (Types.PRICE | Types.COMPARE) & Types.PRICE == Types.PRICE and
        (Types.PRICE | Types.COMPARE) & Types.COMPARE == Types.COMPARE
    )),
    ("test_types_enum_abs_flag", lambda: Types.ABS.value == 0),
    ("test_types_enum_predefined_combination", lambda: (
        (Types.PRECDIFF & Types.PRECENTAGE) == Types.PRECENTAGE and
        (Types.PRECDIFF & Types.DIFF) == Types.DIFF
    )),
]

for test_name, test_func in tests:
    try:
        result = test_func()
        if result:
            print(f"✓ PASSED: {test_name}")
            test_results.append((test_name, "PASSED"))
        else:
            print(f"✗ FAILED: {test_name}")
            test_results.append((test_name, "FAILED"))
    except Exception as e:
        print(f"✗ ERROR: {test_name} - {e}")
        test_results.append((test_name, f"ERROR: {e}"))

# Test UniteType enum
print("\n" + "=" * 70)
print("Testing UniteType enum and bitflag operations")
print("=" * 70)

from common.common import UniteType

tests = [
    ("test_unitetype_enum_individual_flags", lambda: UniteType.SUM.value > 0 and UniteType.AVG.value > 0),
    ("test_unitetype_enum_none_flag", lambda: UniteType.NONE.value == 0),
    ("test_unitetype_enum_combine_flags", lambda: (UniteType.SUM | UniteType.AVG) != 0),
    ("test_unitetype_predefined_combination", lambda: (
        (UniteType.ADDTOTALS & UniteType.ADDPROT) == UniteType.ADDPROT and
        (UniteType.ADDTOTALS & UniteType.ADDTOTAL) == UniteType.ADDTOTAL
    )),
]

for test_name, test_func in tests:
    try:
        result = test_func()
        if result:
            print(f"✓ PASSED: {test_name}")
            test_results.append((test_name, "PASSED"))
        else:
            print(f"✗ FAILED: {test_name}")
            test_results.append((test_name, "FAILED"))
    except Exception as e:
        print(f"✗ ERROR: {test_name} - {e}")
        test_results.append((test_name, f"ERROR: {e}"))

# Print summary
print("\n" + "=" * 70)
print("TEST SUMMARY")
print("=" * 70)

passed = sum(1 for _, status in test_results if status == "PASSED")
failed = sum(1 for _, status in test_results if "FAILED" in status or "ERROR" in status)

print(f"\nTotal: {len(test_results)} tests")
print(f"Passed: {passed}")
print(f"Failed: {failed}")

if failed > 0:
    print("\nFailed/Error tests:")
    for test_name, status in test_results:
        if "FAILED" in status or "ERROR" in status:
            print(f"  - {test_name}: {status}")

print("\n" + "=" * 70)
sys.exit(0 if failed == 0 else 1)
