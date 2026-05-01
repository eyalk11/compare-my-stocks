"""
Tests for ActOnData class and data generation functionality.

Tests cover:
- get_ref_array with 1D and 2D arrays
- handle_operation with PERCENTAGE/DIFF/absolute types
- handle_compare for comparison operations
- Edge cases with NaN and empty arrays
"""

import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import numpy as np
import pandas as pd

# Add the package to path (same pattern as test_tries.py)
sys.path.insert(0, str(Path(os.path.dirname(os.path.abspath(__file__))).parent))

from common.common import Types, NoDataException
from config import config
from processing.actondata import ActOnData


# ============================================================================
# Fixtures for test data
# ============================================================================

@pytest.fixture(autouse=True)
def patch_config_debug():
    """Automatically patch config.Running.Debug for all tests."""
    with patch.object(config.Running, 'Debug', False):
        yield


@pytest.fixture
def mock_input_data():
    """Create a mock InputData object."""
    return MagicMock()


@pytest.fixture
def simple_1d_array():
    """Create a simple 1D numpy array."""
    return np.array([100.0, 110.0, 120.0, 130.0, 140.0])


@pytest.fixture
def simple_2d_array():
    """Create a simple 2D numpy array with 3 stocks and 5 time periods."""
    return np.array([
        [100.0, 110.0, 120.0, 130.0, 140.0],
        [50.0, 55.0, 60.0, 65.0, 70.0],
        [200.0, 210.0, 220.0, 230.0, 240.0]
    ])


@pytest.fixture
def dataframe_2d():
    """Create a DataFrame corresponding to 2D array."""
    return pd.DataFrame({
        'stock1': [140.0, 70.0, 240.0],
        'stock2': [140.0, 70.0, 240.0],
        'stock3': [140.0, 70.0, 240.0]
    })


@pytest.fixture
def array_with_nan():
    """Create an array with NaN values."""
    return np.array([100.0, np.nan, 120.0, np.nan, 140.0])


@pytest.fixture
def array_2d_with_nan():
    """Create a 2D array with NaN values."""
    return np.array([
        [100.0, np.nan, 120.0, 130.0, 140.0],
        [np.nan, 55.0, 60.0, np.nan, 70.0],
        [200.0, 210.0, np.nan, 230.0, 240.0]
    ])


@pytest.fixture
def dataframe_simple():
    """Create a simple DataFrame for testing."""
    data = {
        'A': [100.0, 50.0, 200.0],
        'B': [110.0, 55.0, 210.0],
        'C': [120.0, 60.0, 220.0],
        'D': [130.0, 65.0, 230.0],
        'E': [140.0, 70.0, 240.0]
    }
    return pd.DataFrame(data)


# ============================================================================
# Tests for get_ref_array with 1D arrays
# ============================================================================

class TestGetRefArray1D:
    """Tests for get_ref_array method with 1D arrays."""

    def test_get_ref_array_1d_reltostart(self, simple_1d_array, dataframe_simple, mock_input_data):
        """Test get_ref_array with 1D array using RELTOSTART flag."""
        aod = ActOnData(
            arr=simple_1d_array,
            df=dataframe_simple,
            type=Types.RELTOSTART,
            fulldf=MagicMock(),
            compare_with=None,
            inputData=mock_input_data
        )

        ref_array = aod.get_ref_array(simple_1d_array)
        # RELTOSTART should return the first element
        assert ref_array == 100.0

    def test_get_ref_array_1d_reltoend(self, simple_1d_array, dataframe_simple, mock_input_data):
        """Test get_ref_array with 1D array using RELTOEND flag."""
        aod = ActOnData(
            arr=simple_1d_array,
            df=dataframe_simple,
            type=Types.RELTOEND,
            fulldf=MagicMock(),
            compare_with=None,
            inputData=mock_input_data
        )

        ref_array = aod.get_ref_array(simple_1d_array)
        # RELTOEND should return the last element
        assert ref_array == 140.0

    def test_get_ref_array_1d_reltomax(self, simple_1d_array, dataframe_simple, mock_input_data):
        """Test get_ref_array with 1D array using RELTOMAX flag."""
        aod = ActOnData(
            arr=simple_1d_array,
            df=dataframe_simple,
            type=Types.RELTOMAX,
            fulldf=MagicMock(),
            compare_with=None,
            inputData=mock_input_data
        )

        ref_array = aod.get_ref_array(simple_1d_array)
        # RELTOMAX should return the maximum value
        assert ref_array == 140.0

    def test_get_ref_array_1d_reltomin(self, simple_1d_array, dataframe_simple, mock_input_data):
        """Test get_ref_array with 1D array using RELTOMIN flag."""
        aod = ActOnData(
            arr=simple_1d_array,
            df=dataframe_simple,
            type=Types.RELTOMIN,
            fulldf=MagicMock(),
            compare_with=None,
            inputData=mock_input_data
        )

        ref_array = aod.get_ref_array(simple_1d_array)
        # RELTOMIN should return the minimum value
        assert ref_array == 100.0

    def test_get_ref_array_1d_with_nan_reltomax(self, array_with_nan, dataframe_simple, mock_input_data):
        """Test get_ref_array with 1D array containing NaN using RELTOMAX."""
        aod = ActOnData(
            arr=array_with_nan,
            df=dataframe_simple,
            type=Types.RELTOMAX,
            fulldf=MagicMock(),
            compare_with=None,
            inputData=mock_input_data
        )

        ref_array = aod.get_ref_array(array_with_nan)
        # nanmax should ignore NaN values
        assert ref_array == 140.0

    def test_get_ref_array_1d_with_nan_reltomin(self, array_with_nan, dataframe_simple, mock_input_data):
        """Test get_ref_array with 1D array containing NaN using RELTOMIN."""
        aod = ActOnData(
            arr=array_with_nan,
            df=dataframe_simple,
            type=Types.RELTOMIN,
            fulldf=MagicMock(),
            compare_with=None,
            inputData=mock_input_data
        )

        ref_array = aod.get_ref_array(array_with_nan)
        # nanmin should ignore NaN values
        assert ref_array == 100.0


# ============================================================================
# Tests for get_ref_array with 2D arrays
# ============================================================================

class TestGetRefArray2D:
    """Tests for get_ref_array method with 2D arrays."""

    def test_get_ref_array_2d_reltostart(self, simple_2d_array, dataframe_simple, mock_input_data):
        """Test get_ref_array with 2D array using RELTOSTART flag."""
        aod = ActOnData(
            arr=simple_2d_array,
            df=dataframe_simple,
            type=Types.RELTOSTART,
            fulldf=MagicMock(),
            compare_with=None,
            inputData=mock_input_data
        )

        ref_array = aod.get_ref_array(simple_2d_array)
        # RELTOSTART should return first column ([:, 0])
        expected = np.array([100.0, 50.0, 200.0])
        np.testing.assert_array_equal(ref_array, expected)

    def test_get_ref_array_2d_reltoend(self, simple_2d_array, dataframe_simple, mock_input_data):
        """Test get_ref_array with 2D array using RELTOEND flag."""
        aod = ActOnData(
            arr=simple_2d_array,
            df=dataframe_simple,
            type=Types.RELTOEND,
            fulldf=MagicMock(),
            compare_with=None,
            inputData=mock_input_data
        )

        ref_array = aod.get_ref_array(simple_2d_array)
        # RELTOEND should return last column ([:, -1])
        expected = np.array([140.0, 70.0, 240.0])
        np.testing.assert_array_equal(ref_array, expected)

    def test_get_ref_array_2d_reltomax(self, simple_2d_array, dataframe_simple, mock_input_data):
        """Test get_ref_array with 2D array using RELTOMAX flag."""
        aod = ActOnData(
            arr=simple_2d_array,
            df=dataframe_simple,
            type=Types.RELTOMAX,
            fulldf=MagicMock(),
            compare_with=None,
            inputData=mock_input_data
        )

        ref_array = aod.get_ref_array(simple_2d_array)
        # nanmax along axis 1 should return max for each row
        expected = np.array([140.0, 70.0, 240.0])
        np.testing.assert_array_equal(ref_array, expected)

    def test_get_ref_array_2d_reltomin(self, simple_2d_array, dataframe_simple, mock_input_data):
        """Test get_ref_array with 2D array using RELTOMIN flag."""
        aod = ActOnData(
            arr=simple_2d_array,
            df=dataframe_simple,
            type=Types.RELTOMIN,
            fulldf=MagicMock(),
            compare_with=None,
            inputData=mock_input_data
        )

        ref_array = aod.get_ref_array(simple_2d_array)
        # nanmin along axis 1 should return min for each row
        expected = np.array([100.0, 50.0, 200.0])
        np.testing.assert_array_equal(ref_array, expected)

    def test_get_ref_array_2d_with_nan_reltomax(self, array_2d_with_nan, dataframe_simple, mock_input_data):
        """Test get_ref_array with 2D array containing NaN using RELTOMAX."""
        aod = ActOnData(
            arr=array_2d_with_nan,
            df=dataframe_simple,
            type=Types.RELTOMAX,
            fulldf=MagicMock(),
            compare_with=None,
            inputData=mock_input_data
        )

        ref_array = aod.get_ref_array(array_2d_with_nan)
        # nanmax along axis 1, ignoring NaN
        expected = np.array([140.0, 70.0, 240.0])
        np.testing.assert_array_equal(ref_array, expected)

    def test_get_ref_array_2d_empty_columns_raises(self, mock_input_data):
        """Test get_ref_array raises NoDataException with empty 2D array."""
        empty_2d = np.empty((3, 0))

        aod = ActOnData(
            arr=empty_2d,
            df=MagicMock(),
            type=Types.RELTOMAX,
            fulldf=MagicMock(),
            compare_with=None,
            inputData=mock_input_data
        )

        with pytest.raises(NoDataException):
            aod.get_ref_array(empty_2d)


# ============================================================================
# Tests for handle_operation
# ============================================================================

class TestHandleOperation:
    """Tests for handle_operation method with different operation types."""

    def test_handle_operation_absolute(self, simple_2d_array, dataframe_simple, mock_input_data):
        """Test handle_operation with absolute (default) type."""
        aod = ActOnData(
            arr=simple_2d_array,
            df=dataframe_simple,
            type=Types.ABS,
            fulldf=MagicMock(),
            compare_with=None,
            inputData=mock_input_data
        )
        # Set refarr (needed by handle_operation)
        aod.refarr = np.array([100.0, 50.0, 200.0])

        result = aod.handle_operation()
        # With ABS type, result should equal transpose_arr
        np.testing.assert_array_equal(result, simple_2d_array.transpose())

    def test_handle_operation_diff(self, simple_2d_array, dataframe_simple, mock_input_data):
        """Test handle_operation with DIFF type."""
        aod = ActOnData(
            arr=simple_2d_array,
            df=dataframe_simple,
            type=Types.DIFF,
            fulldf=MagicMock(),
            compare_with=None,
            inputData=mock_input_data
        )
        # Set refarr for DIFF calculation
        aod.refarr = np.array([100.0, 50.0, 200.0])

        result = aod.handle_operation()
        # With DIFF type: transpose_arr - refarr
        # Verify shape and basic properties
        assert result.shape == (5, 3)  # transposed from 3x5
        # Verify first element calculation: 100 - 100 = 0
        assert result[0, 0] == 0.0
        # Verify last element calculation: 140 - 100 = 40
        assert result[-1, 0] == 40.0

    def test_handle_operation_percentage(self, simple_2d_array, dataframe_simple, mock_input_data):
        """Test handle_operation with PERCENTAGE type."""
        aod = ActOnData(
            arr=simple_2d_array,
            df=dataframe_simple,
            type=Types.PRECENTAGE,
            fulldf=MagicMock(),
            compare_with=None,
            inputData=mock_input_data
        )
        # Set refarr for PERCENTAGE calculation
        aod.refarr = np.array([100.0, 50.0, 200.0])

        result = aod.handle_operation()
        # With PERCENTAGE: (transpose_arr / refarr) * 100 calculation
        # Verify shape is correct
        assert result.shape == (5, 3)  # transposed from 3x5
        # Verify result is numeric array
        assert isinstance(result, np.ndarray)

    def test_handle_operation_percentage_with_reltostart(self, simple_2d_array, dataframe_simple, mock_input_data):
        """Test handle_operation with PERCENTAGE and RELTOSTART flags."""
        aod = ActOnData(
            arr=simple_2d_array,
            df=dataframe_simple,
            type=Types.PRECENTAGE | Types.RELTOSTART,
            fulldf=MagicMock(),
            compare_with=None,
            inputData=mock_input_data
        )
        # Set refarr for PERCENTAGE calculation
        aod.refarr = np.array([100.0, 50.0, 200.0])

        result = aod.handle_operation()
        # With PERCENTAGE and RELTOSTART: (transpose_arr / refarr - 1) * 100
        # Verify shape and basic properties
        assert result.shape == (5, 3)  # transposed from 3x5
        # Verify first element: (100/100 - 1) * 100 = 0
        assert result[0, 0] == 0.0

    def test_handle_operation_with_nan_values(self, array_2d_with_nan, dataframe_simple, mock_input_data):
        """Test handle_operation handles NaN values correctly."""
        aod = ActOnData(
            arr=array_2d_with_nan,
            df=dataframe_simple,
            type=Types.DIFF,
            fulldf=MagicMock(),
            compare_with=None,
            inputData=mock_input_data
        )
        aod.refarr = np.array([100.0, 50.0, 200.0])

        result = aod.handle_operation()
        # Result should contain NaN where input had NaN
        assert np.isnan(result[0, 1])  # Second column, first row was NaN
        assert np.isnan(result[1, 0])  # First column, second row was NaN


# ============================================================================
# Tests for handle_compare
# ============================================================================

class TestHandleCompare:
    """Tests for handle_compare method."""

    def test_handle_compare_method_exists(self, simple_2d_array, dataframe_simple, mock_input_data):
        """Test that handle_compare method exists and is callable."""
        # Create a comparison array (1D)
        compit_arr = np.array([100.0, 50.0, 200.0])

        # Create mock fulldf with the comparison column
        fulldf_mock = MagicMock()
        fulldf_mock.__getitem__ = MagicMock(return_value=compit_arr)

        arr_copy = simple_2d_array.copy()
        aod = ActOnData(
            arr=arr_copy,
            df=dataframe_simple,
            type=Types.DIFF,
            fulldf=fulldf_mock,
            compare_with='QQQ',
            inputData=mock_input_data
        )
        aod.refarr = np.array([100.0, 50.0, 200.0])

        # Verify the method exists and is callable
        assert hasattr(aod, 'handle_compare')
        assert callable(aod.handle_compare)

    def test_handle_compare_diff(self, mock_input_data):
        """COMPARE | DIFF: result is (stock_price - benchmark_price) per row."""
        # 3 stocks, 5 timestamps each
        arr = np.array([
            [100.0, 110.0, 120.0, 130.0, 140.0],   # A
            [50.0, 55.0, 60.0, 65.0, 70.0],        # B
            [200.0, 210.0, 220.0, 230.0, 240.0],   # C
        ])
        df = pd.DataFrame({'A': np.zeros(5), 'B': np.zeros(5), 'C': np.zeros(5)})
        # benchmark series, length == number of timestamps
        compit_arr = np.array([100.0, 105.0, 110.0, 115.0, 120.0])
        fulldf = pd.DataFrame({'QQQ': compit_arr})

        aod = ActOnData(
            arr=arr, df=df, type=Types.COMPARE | Types.DIFF,
            fulldf=fulldf, compare_with='QQQ', inputData=mock_input_data,
        )
        aod.do()

        # ign=False for plain COMPARE (no PRECENTAGE) → handle_operation runs
        # AFTER handle_compare overwrites transpose_arr with (stock - benchmark).
        # refarr was computed before handle_compare: first column [100, 50, 200].
        # First row: (stock-benchmark) - refarr = [0,-50,100] - [100,50,200] = [-100,-100,-100]
        # Last row: [20,-50,120] - [100,50,200] = [-80,-100,-80]
        np.testing.assert_array_almost_equal(aod.newarr[0], [-100.0, -100.0, -100.0])
        np.testing.assert_array_almost_equal(aod.newarr[-1], [-80.0, -100.0, -80.0])

    def test_handle_compare_percentage(self, mock_input_data):
        """COMPARE | PRECENTAGE: relative outperformance vs benchmark, in %."""
        arr = np.array([
            [100.0, 110.0, 120.0],   # A: +20%
            [200.0, 220.0, 260.0],   # B: +30%
        ])
        df = pd.DataFrame({'A': np.zeros(3), 'B': np.zeros(3)})
        compit_arr = np.array([100.0, 105.0, 110.0])  # benchmark: +10%
        fulldf = pd.DataFrame({'QQQ': compit_arr})

        aod = ActOnData(
            arr=arr, df=df, type=Types.COMPARE | Types.PRECENTAGE,
            fulldf=fulldf, compare_with='QQQ', inputData=mock_input_data,
        )
        aod.do()

        # ign=True path: newarr = ((arr/refarr) / (compit/compit_initial) - 1) * 100
        # refarr defaults to first column ([100, 200]); compit_initial = 100.
        # First row: ((100/100)/(100/100) - 1)*100 = 0 for both → [0, 0]
        np.testing.assert_array_almost_equal(aod.newarr[0], [0.0, 0.0])
        # Last row A: ((120/100)/(110/100) - 1)*100 = (1.2/1.1 - 1)*100 ≈ 9.0909
        # Last row B: ((260/200)/(110/100) - 1)*100 = (1.3/1.1 - 1)*100 ≈ 18.1818
        np.testing.assert_array_almost_equal(
            aod.newarr[-1], [9.0909090909, 18.1818181818], decimal=6
        )

    def test_handle_compare_percentage_diff(self, mock_input_data):
        """COMPARE | PRECENTAGE | DIFF: difference of percent changes."""
        arr = np.array([
            [100.0, 110.0, 120.0],   # +20%
            [200.0, 220.0, 260.0],   # +30%
        ])
        df = pd.DataFrame({'A': np.zeros(3), 'B': np.zeros(3)})
        compit_arr = np.array([100.0, 105.0, 110.0])  # +10%
        fulldf = pd.DataFrame({'QQQ': compit_arr})

        aod = ActOnData(
            arr=arr, df=df,
            type=Types.COMPARE | Types.PRECENTAGE | Types.DIFF,
            fulldf=fulldf, compare_with='QQQ', inputData=mock_input_data,
        )
        aod.do()

        # newarr = (arr/refarr - compit/compit_initial) * 100
        # Last row A: (120/100 - 110/100)*100 = 10
        # Last row B: (260/200 - 110/100)*100 = (1.3 - 1.1)*100 = 20
        np.testing.assert_array_almost_equal(aod.newarr[0], [0.0, 0.0])
        np.testing.assert_array_almost_equal(aod.newarr[-1], [10.0, 20.0])


# ============================================================================
# Tests for fixinf
# ============================================================================

class TestFixInf:
    """Tests for fixinf method."""

    def test_fixinf_replaces_infinity(self):
        """Test that fixinf replaces infinity with NaN."""
        arr = np.array([1.0, np.inf, 3.0, -np.inf, 5.0])
        dataframe = pd.DataFrame({'A': [1, 2, 3]})

        aod = ActOnData(
            arr=arr,
            df=dataframe,
            type=Types.ABS,
            fulldf=MagicMock(),
            compare_with=None,
            inputData=MagicMock()
        )

        result = aod.fixinf(arr.copy())

        # Check that inf values are replaced with NaN
        assert np.isnan(result[1])  # np.inf -> NaN
        assert np.isnan(result[3])  # -np.inf -> NaN
        assert result[0] == 1.0
        assert result[4] == 5.0

    def test_fixinf_preserves_valid_values(self):
        """Test that fixinf preserves valid numerical values."""
        arr = np.array([100.0, 110.0, 120.0, np.nan, 140.0])
        dataframe = pd.DataFrame({'A': [1, 2, 3]})

        aod = ActOnData(
            arr=arr,
            df=dataframe,
            type=Types.ABS,
            fulldf=MagicMock(),
            compare_with=None,
            inputData=MagicMock()
        )

        result = aod.fixinf(arr.copy())

        # Check that valid values are unchanged
        assert result[0] == 100.0
        assert result[1] == 110.0
        assert np.isnan(result[3])  # NaN preserved


# ============================================================================
# Tests for edge cases
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_get_ref_array_all_nan_1d(self, dataframe_simple, mock_input_data):
        """Test get_ref_array with all NaN values in 1D array."""
        all_nan = np.array([np.nan, np.nan, np.nan])

        aod = ActOnData(
            arr=all_nan,
            df=dataframe_simple,
            type=Types.RELTOMAX,
            fulldf=MagicMock(),
            compare_with=None,
            inputData=mock_input_data
        )

        result = aod.get_ref_array(all_nan)
        # nanmax of all NaN should return NaN
        assert np.isnan(result)

    def test_get_ref_array_all_nan_2d(self, dataframe_simple, mock_input_data):
        """Test get_ref_array with all NaN values in 2D array."""
        all_nan_2d = np.full((3, 5), np.nan)

        aod = ActOnData(
            arr=all_nan_2d,
            df=dataframe_simple,
            type=Types.RELTOMAX,
            fulldf=MagicMock(),
            compare_with=None,
            inputData=mock_input_data
        )

        result = aod.get_ref_array(all_nan_2d)
        # All results should be NaN
        assert np.all(np.isnan(result))

    def test_handle_operation_single_element(self, dataframe_simple, mock_input_data):
        """Test handle_operation with a single element array."""
        single = np.array([[100.0]])

        aod = ActOnData(
            arr=single,
            df=dataframe_simple,
            type=Types.DIFF,
            fulldf=MagicMock(),
            compare_with=None,
            inputData=mock_input_data
        )
        aod.refarr = np.array([100.0])

        result = aod.handle_operation()
        # Result should be 0 (100 - 100)
        assert result[0, 0] == 0.0

    def test_transpose_arr_initialization(self, simple_2d_array, dataframe_simple, mock_input_data):
        """Test that transpose_arr is correctly initialized."""
        aod = ActOnData(
            arr=simple_2d_array,
            df=dataframe_simple,
            type=Types.ABS,
            fulldf=MagicMock(),
            compare_with=None,
            inputData=mock_input_data
        )

        # transpose_arr should be created during __init__
        expected = simple_2d_array.transpose()
        np.testing.assert_array_equal(aod.transpose_arr, expected)

    def test_zero_division_in_percentage(self, dataframe_simple, mock_input_data):
        """Test handle_operation with zero values in refarr (division case)."""
        arr = np.array([[1.0, 2.0], [3.0, 4.0]])

        aod = ActOnData(
            arr=arr,
            df=dataframe_simple,
            type=Types.PRECENTAGE,
            fulldf=MagicMock(),
            compare_with=None,
            inputData=mock_input_data
        )
        # Set refarr with zero value
        aod.refarr = np.array([0.0, 10.0])

        result = aod.handle_operation()
        # Division by zero should result in inf
        assert np.isinf(result[0, 0]) or np.isnan(result[0, 0])

    def test_negative_values_in_arrays(self, dataframe_simple, mock_input_data):
        """Test that operations handle negative values correctly."""
        neg_array = np.array([[-100.0, -110.0], [50.0, 60.0]])

        aod = ActOnData(
            arr=neg_array,
            df=dataframe_simple,
            type=Types.DIFF,
            fulldf=MagicMock(),
            compare_with=None,
            inputData=mock_input_data
        )
        aod.refarr = np.array([-100.0, 50.0])

        result = aod.handle_operation()
        # DIFF operation on negative values
        # Verify shape and basic calculations
        assert result.shape == (2, 2)  # transposed from 2x2
        # First element: -100 - (-100) = 0
        assert result[0, 0] == 0.0
        # Second row, first element: 50 - 50 = 0
        assert result[0, 1] == 0.0


# ============================================================================
# Integration tests
# ============================================================================

class TestActOnDataIntegration:
    """Integration tests combining multiple ActOnData operations."""

    def test_full_workflow_with_percentage(self, simple_2d_array, dataframe_simple, mock_input_data):
        """Test a complete workflow: get_ref_array -> handle_operation -> fixinf."""
        arr = simple_2d_array.copy()

        aod = ActOnData(
            arr=arr,
            df=dataframe_simple,
            type=Types.PRECENTAGE | Types.RELTOSTART,
            fulldf=MagicMock(),
            compare_with=None,
            inputData=mock_input_data
        )

        # Step 1: get_ref_array
        aod.refarr = aod.get_ref_array(aod.arr)

        # Step 2: handle_operation
        result = aod.handle_operation()

        # Step 3: fixinf
        final = aod.fixinf(result)

        # Verify the result has expected shape and values
        assert final.shape == (5, 3)  # transposed from 3x5
        # First row should be all 0% (relative to start)
        np.testing.assert_array_almost_equal(final[0], [0.0, 0.0, 0.0])

    def test_full_workflow_with_nan_handling(self, array_2d_with_nan, dataframe_simple, mock_input_data):
        """Test workflow with NaN values included."""
        arr = array_2d_with_nan.copy()

        aod = ActOnData(
            arr=arr,
            df=dataframe_simple,
            type=Types.PRECENTAGE | Types.RELTOMAX,
            fulldf=MagicMock(),
            compare_with=None,
            inputData=mock_input_data
        )

        # Get reference array (handles NaN)
        aod.refarr = aod.get_ref_array(aod.arr)

        # Handle operation
        result = aod.handle_operation()

        # Fix infinity
        final = aod.fixinf(result)

        # Verify result shape
        assert final.shape == (5, 3)


# ============================================================================
# DataGenerator.unite_groups
# ============================================================================

from common.common import UniteType
from processing.datagenerator import DataGenerator


def _make_unite_dg(params_groups, group_members, used_unitetype,
                   df, *, weighted_for_portfolio=False, portfolio=None,
                   required_syms_result=None):
    """Build a minimal DataGenerator that exercises only unite_groups."""
    dg = DataGenerator.__new__(DataGenerator)
    eng = MagicMock()
    eng.Groups = group_members
    eng.required_syms = MagicMock(return_value=required_syms_result or set())
    eng.input_processor.get_portfolio_stocks = MagicMock(
        return_value=list(portfolio or []))
    eng.params.groups = params_groups
    eng.params.weighted_for_portfolio = weighted_for_portfolio
    dg._eng = eng
    dg.used_unitetype = used_unitetype
    return dg


class TestUniteGroups:
    """unite_groups collapses each group's stocks into a single per-group
    column. With non-trivial unite (SUM/AVG/...), ndf starts empty and
    only the unite columns plus required_syms are kept. With trivial
    unite (just ADDTOTALS), ndf keeps every original column and just
    appends 'All' or 'Portfolio'."""

    def _df(self, dates, stock_values):
        """stock_values: dict[stock_name → list[value]]"""
        return pd.DataFrame(stock_values, index=pd.to_datetime(dates))

    def test_sum_yields_column_per_group(self):
        df = self._df(['2024-01-01', '2024-01-02'],
                      {'A': [10.0, 11.0], 'B': [20.0, 22.0],
                       'C': [5.0, 6.0]})
        dg = _make_unite_dg(
            params_groups=['G1', 'G2'],
            group_members={'G1': ['A', 'B'], 'G2': ['C']},
            used_unitetype=UniteType.SUM, df=df,
        )
        ndf, cols = dg.unite_groups(df)
        assert 'G1' in ndf.columns
        assert 'G2' in ndf.columns
        # G1 = A + B = [30, 33]; G2 = C = [5, 6]
        assert list(ndf['G1']) == [30.0, 33.0]
        assert list(ndf['G2']) == [5.0, 6.0]

    def test_avg_yields_mean_per_group(self):
        df = self._df(['2024-01-01'],
                      {'A': [10.0], 'B': [20.0], 'C': [30.0]})
        dg = _make_unite_dg(
            params_groups=['G1'],
            group_members={'G1': ['A', 'B', 'C']},
            used_unitetype=UniteType.AVG, df=df,
        )
        ndf, _ = dg.unite_groups(df)
        # mean of [10, 20, 30] = 20
        assert ndf['G1'].iloc[0] == pytest.approx(20.0)

    def test_addtotal_appends_all_column_with_sum(self):
        """Trivial unite (ADDTOTAL only) keeps every original stock column
        AND appends 'All' = sum of required_syms."""
        df = self._df(['2024-01-01'], {'A': [10.0], 'B': [20.0]})
        dg = _make_unite_dg(
            params_groups=[], group_members={},
            used_unitetype=UniteType.ADDTOTAL, df=df,
            required_syms_result={'A', 'B'},
        )
        ndf, _ = dg.unite_groups(df)
        # Original cols preserved.
        assert 'A' in ndf.columns
        assert 'B' in ndf.columns
        # 'All' appended with sum.
        assert 'All' in ndf.columns
        assert ndf['All'].iloc[0] == pytest.approx(30.0)

    def test_sum_handles_overlapping_groups(self):
        """Stock present in multiple groups counted in each group's sum."""
        df = self._df(['2024-01-01'],
                      {'A': [10.0], 'B': [20.0], 'C': [30.0]})
        dg = _make_unite_dg(
            params_groups=['G1', 'G2'],
            group_members={'G1': ['A', 'B'], 'G2': ['B', 'C']},
            used_unitetype=UniteType.SUM, df=df,
        )
        ndf, _ = dg.unite_groups(df)
        assert ndf['G1'].iloc[0] == pytest.approx(30.0)  # A+B
        assert ndf['G2'].iloc[0] == pytest.approx(50.0)  # B+C

    def test_missing_stock_in_group_is_silently_skipped(self):
        """If a group references a stock that isn't in df, it just gets
        dropped from that group's sum (no exception)."""
        df = self._df(['2024-01-01'], {'A': [10.0]})
        dg = _make_unite_dg(
            params_groups=['G1'],
            group_members={'G1': ['A', 'B_MISSING']},  # B is not in df
            used_unitetype=UniteType.SUM, df=df,
        )
        ndf, _ = dg.unite_groups(df)
        assert ndf['G1'].iloc[0] == pytest.approx(10.0)

    def test_portfolio_in_params_groups_unites_portfolio_stocks(self):
        """Selecting 'Portfolio' as a group unites get_portfolio_stocks(),
        not Groups['Portfolio'] (which doesn't exist) — regression for
        KeyError: 'Portfolio'."""
        df = self._df(['2024-01-01'],
                      {'A': [10.0], 'B': [20.0], 'C': [30.0]})
        dg = _make_unite_dg(
            params_groups=['Portfolio'],
            group_members={},  # 'Portfolio' is NOT a real group
            used_unitetype=UniteType.SUM, df=df,
            portfolio=['A', 'B'],
        )
        ndf, _ = dg.unite_groups(df)
        assert 'Portfolio' in ndf.columns
        assert ndf['Portfolio'].iloc[0] == pytest.approx(30.0)  # A+B

    def test_unknown_group_is_skipped_not_raised(self):
        """A stale group name in params.groups that's not in Groups is
        skipped with a warning rather than raising KeyError."""
        df = self._df(['2024-01-01'], {'A': [10.0], 'B': [20.0]})
        dg = _make_unite_dg(
            params_groups=['G1', 'GhostGroup'],
            group_members={'G1': ['A']},
            used_unitetype=UniteType.SUM, df=df,
        )
        ndf, _ = dg.unite_groups(df)
        assert 'G1' in ndf.columns
        assert 'GhostGroup' not in ndf.columns

    @pytest.mark.xfail(reason="Bug: unite_groups only implements SUM and "
                              "AVG (datagenerator.py:236-247). UniteType.MIN "
                              "and UniteType.MAX are defined in common.py:175-176 "
                              "but no codepath sets ndf[gr], so the column "
                              "never appears. Probably dead UI options.",
                       strict=True)
    def test_min_yields_per_date_minimum(self):
        df = self._df(['2024-01-01'],
                      {'A': [10.0], 'B': [20.0], 'C': [30.0]})
        dg = _make_unite_dg(
            params_groups=['G1'],
            group_members={'G1': ['A', 'B', 'C']},
            used_unitetype=UniteType.MIN, df=df,
        )
        ndf, _ = dg.unite_groups(df)
        assert 'G1' in ndf.columns
        assert ndf['G1'].iloc[0] == pytest.approx(10.0)
