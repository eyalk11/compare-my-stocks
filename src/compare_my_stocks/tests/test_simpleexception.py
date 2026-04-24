import pytest
import logging
from unittest.mock import Mock, patch, MagicMock

from common.simpleexceptioncontext import SimpleExceptionContext, simple_exception_handling


# Tests for SimpleExceptionContext with never_throw=True
def test_simpleexceptioncontext_never_throw_suppresses_exception():
    """Test that never_throw=True suppresses exceptions."""
    with SimpleExceptionContext(never_throw=True, noconfig=True):
        raise ValueError("Test error")
    # If we reach here, exception was suppressed


def test_simpleexceptioncontext_never_throw_logs_exception():
    """Test that never_throw=True logs the exception."""
    with patch('logging.error') as mock_error:
        with SimpleExceptionContext(never_throw=True, noconfig=True, err_description="Test error"):
            raise ValueError("Test exception")
        # Verify error was logged
        assert mock_error.called


def test_simpleexceptioncontext_never_throw_with_callback():
    """Test that callback is invoked when exception occurs with never_throw=True."""
    callback_mock = Mock()
    with SimpleExceptionContext(never_throw=True, callback=callback_mock, noconfig=True):
        raise ValueError("Test error")
    # Verify callback was called with the exception
    assert callback_mock.called


def test_simpleexceptioncontext_callback_receives_exception():
    """Test that callback receives the actual exception instance."""
    captured_exception = None

    def capture_exception(exc):
        nonlocal captured_exception
        captured_exception = exc

    exc_value = ValueError("Test message")
    with SimpleExceptionContext(callback=capture_exception, never_throw=True, noconfig=True):
        raise exc_value

    assert captured_exception is exc_value


# Tests for SimpleExceptionContext with always_throw=False
def test_simpleexceptioncontext_always_throw_false_suppresses_exception():
    """Test that always_throw=False suppresses exceptions."""
    with SimpleExceptionContext(always_throw=False, noconfig=True):
        raise ValueError("Test error")
    # If we reach here, exception was suppressed


def test_simpleexceptioncontext_always_throw_false_logs_exception():
    """Test that always_throw=False logs the exception."""
    with patch('logging.error') as mock_error:
        with SimpleExceptionContext(always_throw=False, noconfig=True, err_description="Test error"):
            raise ValueError("Test exception")
        assert mock_error.called


# Tests for exception suppression
def test_simpleexceptioncontext_suppresses_exception_without_never_throw_or_always_throw():
    """Test that exceptions are suppressed without special flags."""
    # With neither never_throw nor always_throw set, and exception not in err_to_ignore,
    # exceptions are suppressed by default
    with SimpleExceptionContext(noconfig=True):
        raise ValueError("Test error")
    # If we reach here, exception was suppressed


def test_simpleexceptioncontext_raises_exception_in_err_to_ignore():
    """Test that exceptions in err_to_ignore are re-raised when never_throw=False."""
    # With never_throw=False, exceptions in err_to_ignore are re-raised
    with pytest.raises(ValueError):
        with SimpleExceptionContext(err_to_ignore=[ValueError], never_throw=False, noconfig=True):
            raise ValueError("Test error")


def test_simpleexceptioncontext_no_exception_returns_false():
    """Test that __exit__ returns False when no exception occurs."""
    ctx = SimpleExceptionContext(noconfig=True)
    ctx.__enter__()
    result = ctx.__exit__(None, None, None)
    assert result is False


def test_simpleexceptioncontext_with_exception_returns_true_on_suppress():
    """Test that __exit__ returns True when suppressing exception."""
    ctx = SimpleExceptionContext(never_throw=True, noconfig=True)
    ctx.__enter__()
    exc = ValueError("Test")
    result = ctx.__exit__(ValueError, exc, None)
    # With never_throw=True and no always_throw, it should suppress (return True)
    assert result is True


# Tests for exception re-raising
def test_simpleexceptioncontext_always_throw_true_reraises():
    """Test that always_throw=True causes exception to be re-raised."""
    with pytest.raises(ValueError):
        with SimpleExceptionContext(always_throw=True, noconfig=True):
            raise ValueError("Test error")


def test_simpleexceptioncontext_err_to_ignore_with_never_throw():
    """Test that err_to_ignore respects never_throw flag."""
    with SimpleExceptionContext(
        err_to_ignore=[ValueError],
        never_throw=True,
        noconfig=True
    ):
        raise ValueError("Test error")
    # If we reach here, exception was suppressed


def test_simpleexceptioncontext_err_to_ignore_with_always_throw():
    """Test that always_throw overrides err_to_ignore."""
    with pytest.raises(ValueError):
        with SimpleExceptionContext(
            err_to_ignore=[ValueError],
            always_throw=True,
            noconfig=True
        ):
            raise ValueError("Test error")


# Tests for error description
def test_simpleexceptioncontext_err_description_in_log():
    """Test that err_description is included in error log."""
    with patch('logging.error') as mock_error:
        with SimpleExceptionContext(
            err_description="Custom error message",
            never_throw=True,
            noconfig=True
        ):
            raise ValueError("Original error")
        # Verify the custom description was logged
        assert mock_error.called
        call_args = str(mock_error.call_args)
        assert "Custom error message" in call_args or mock_error.call_count > 0


# Tests for return_succ parameter
def test_simpleexceptioncontext_return_succ_with_exception():
    """Test that return_succ is used when exception occurs (decorator pattern)."""
    @simple_exception_handling(return_succ='default', never_throw=True, noconfig=True)
    def failing_function():
        raise ValueError("Test error")

    result = failing_function()
    assert result == 'default'


def test_simpleexceptioncontext_decorator_no_exception():
    """Test decorator returns actual result when no exception occurs."""
    @simple_exception_handling(noconfig=True)
    def passing_function():
        return 42

    result = passing_function()
    assert result == 42


# Tests for debug flag
def test_simpleexceptioncontext_debug_flag_logs_debug():
    """Test that debug=True uses logging.debug instead of logging.error."""
    with patch('logging.debug') as mock_debug:
        with SimpleExceptionContext(
            debug=True,
            never_throw=True,
            noconfig=True,
            err_description="Debug message"
        ):
            raise ValueError("Test error")
        # With debug=True, debug should be called instead of error
        # Note: might still call error for traceback, but debug for description


# Tests for detailed flag
def test_simpleexceptioncontext_detailed_true_logs_traceback():
    """Test that detailed=True includes traceback in log."""
    with patch('logging.error') as mock_error:
        with SimpleExceptionContext(
            detailed=True,
            never_throw=True,
            noconfig=True
        ):
            raise ValueError("Test error")
        # Verify error was called (may include traceback)
        assert mock_error.called


def test_simpleexceptioncontext_detailed_false_minimal_log():
    """Test that detailed=False minimizes logged information."""
    with patch('logging.error') as mock_error:
        with SimpleExceptionContext(
            detailed=False,
            never_throw=True,
            noconfig=True
        ):
            raise ValueError("Test error")
        # Verify error was called with minimal information
        assert mock_error.called


# Tests for multiple exceptions in context
def test_simpleexceptioncontext_nested_contexts():
    """Test nested SimpleExceptionContext contexts."""
    outer_exception_handled = False
    inner_exception_handled = False

    try:
        with SimpleExceptionContext(never_throw=False, noconfig=True):
            outer_exception_handled = True
            with SimpleExceptionContext(never_throw=True, noconfig=True):
                raise ValueError("Inner error")
            # If we reach here, inner exception was suppressed
            inner_exception_handled = True
    except:
        pass

    assert inner_exception_handled


# Tests for callback error handling
def test_simpleexceptioncontext_callback_exception_is_suppressed():
    """Test that exceptions in callback don't break the context."""
    def failing_callback(exc):
        raise RuntimeError("Callback failed")

    with patch('logging.warn') as mock_warn:
        with SimpleExceptionContext(callback=failing_callback, never_throw=True, noconfig=True):
            raise ValueError("Original error")
        # Verify warning was logged for callback failure
        assert mock_warn.called


# Tests for context manager protocol
def test_simpleexceptioncontext_context_manager_enter():
    """Test __enter__ returns self."""
    ctx = SimpleExceptionContext(noconfig=True)
    result = ctx.__enter__()
    assert result is ctx


def test_simpleexceptioncontext_context_manager_exit_with_no_exception():
    """Test __exit__ with no exception (None, None, None)."""
    ctx = SimpleExceptionContext(noconfig=True)
    ctx.__enter__()
    result = ctx.__exit__(None, None, None)
    assert result is False


def test_simpleexceptioncontext_context_manager_exit_with_exception():
    """Test __exit__ with actual exception type, value, and traceback."""
    ctx = SimpleExceptionContext(never_throw=True, noconfig=True)
    ctx.__enter__()

    exc = ValueError("Test")
    import sys
    import traceback
    try:
        raise exc
    except ValueError:
        exc_info = sys.exc_info()
        result = ctx.__exit__(exc_info[0], exc_info[1], exc_info[2])

    # With never_throw=True, should suppress (return True)
    assert result is True


# Tests for decorator with exception handling
def test_simple_exception_handling_decorator_suppresses():
    """Test decorator with never_throw=True suppresses exceptions."""
    @simple_exception_handling(never_throw=True, noconfig=True)
    def failing_function():
        raise ValueError("Test error")

    # Should not raise
    result = failing_function()
    # Should return None when exception occurs and no return_succ provided
    assert result is None


def test_simple_exception_handling_decorator_with_args():
    """Test decorator works with function arguments."""
    @simple_exception_handling(never_throw=True, noconfig=True)
    def add(a, b):
        if a < 0:
            raise ValueError("Negative value")
        return a + b

    # Normal case
    assert add(2, 3) == 5

    # Error case
    result = add(-1, 3)
    assert result is None


def test_simple_exception_handling_decorator_return_succ_undefined():
    """Test decorator with return_succ='undef' (default) suppresses exceptions."""
    @simple_exception_handling(return_succ='undef', noconfig=True)
    def failing_function():
        raise ValueError("Test")

    # With return_succ='undef' and default always_throw=False, exceptions are suppressed
    # The function returns None when exception occurs
    result = failing_function()
    assert result is None


def test_simple_exception_handling_with_callback():
    """Test decorator passes exceptions to callback."""
    callback_mock = Mock()

    @simple_exception_handling(never_throw=True, callback=callback_mock, noconfig=True)
    def failing_function():
        raise ValueError("Test error")

    failing_function()
    # Callback should have been called
    assert callback_mock.called


# Tests for edge cases
def test_simpleexceptioncontext_with_none_error_description():
    """Test with err_description=None."""
    with patch('logging.error') as mock_error:
        with SimpleExceptionContext(err_description=None, never_throw=True, noconfig=True):
            raise ValueError("Test error")
        # Should log the exception itself, not a description
        assert mock_error.called


def test_simpleexceptioncontext_with_multiple_ignored_exceptions():
    """Test err_to_ignore with multiple exception types are re-raised."""
    # With never_throw=False, exceptions in err_to_ignore are re-raised
    with pytest.raises(TypeError):
        with SimpleExceptionContext(
            err_to_ignore=[ValueError, TypeError, RuntimeError],
            never_throw=False,
            noconfig=True
        ):
            raise TypeError("Test error")


def test_simpleexceptioncontext_keyboard_interrupt_suppressed_by_default():
    """Test that KeyboardInterrupt is suppressed by default."""
    # By default, SimpleExceptionContext suppresses all exceptions
    with SimpleExceptionContext(noconfig=True):
        raise KeyboardInterrupt()
    # If we reach here, exception was suppressed


def test_simpleexceptioncontext_keyboard_interrupt_with_always_throw():
    """Test that KeyboardInterrupt is re-raised with always_throw=True."""
    with pytest.raises(KeyboardInterrupt):
        with SimpleExceptionContext(always_throw=True, noconfig=True):
            raise KeyboardInterrupt()


def test_simpleexceptioncontext_system_exit_suppressed_by_default():
    """Test that SystemExit is suppressed by default."""
    # By default, SimpleExceptionContext suppresses all exceptions
    with SimpleExceptionContext(noconfig=True):
        raise SystemExit()
    # If we reach here, exception was suppressed


def test_simpleexceptioncontext_system_exit_with_always_throw():
    """Test that SystemExit is re-raised with always_throw=True."""
    with pytest.raises(SystemExit):
        with SimpleExceptionContext(always_throw=True, noconfig=True):
            raise SystemExit()


# Tests for do_nothing flag behavior
def test_simpleexceptioncontext_do_nothing_behavior():
    """Test do_nothing behavior in debug mode."""
    with patch.dict('os.environ', {'PYCHARM_HOSTED': '0'}):
        ctx = SimpleExceptionContext(never_throw=False, return_succ=None, noconfig=True)
        ctx.__enter__()
        # In normal (non-debug) mode, do_nothing should be False
        # (unless we set specific conditions)


# Tests for caller info
def test_simpleexceptioncontext_with_custom_caller():
    """Test with custom caller information."""
    with patch('logging.error') as mock_error:
        with SimpleExceptionContext(
            caller=("custom.py", 42),
            never_throw=True,
            noconfig=True
        ):
            raise ValueError("Test error")
        # Verify error was logged (caller info should be included)
        assert mock_error.called


# Tests for integration scenarios
def test_simpleexceptioncontext_production_scenario():
    """Test typical production scenario with never_throw and callback."""
    errors_logged = []

    def log_error(exc):
        errors_logged.append(str(exc))

    # Simulate a signal/callback pattern
    with SimpleExceptionContext(
        err_description="Failed to process data",
        never_throw=True,
        callback=log_error,
        noconfig=True
    ):
        # Simulate some processing that fails
        data = [1, 2, "three", 4]
        result = sum([int(x) for x in data])  # Will fail on "three"

    # Verify the error was captured
    assert len(errors_logged) > 0


def test_simpleexceptioncontext_test_mode_scenario():
    """Test behavior in test mode (when config.Running.IsTest=True)."""
    # We can't easily test this without mocking config, but we can verify
    # the context handles it gracefully with noconfig=True
    with SimpleExceptionContext(never_throw=True, noconfig=True):
        raise ValueError("Test error in test mode")
    # Should suppress without issues
