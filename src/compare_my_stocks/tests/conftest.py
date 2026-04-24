import sys
from unittest.mock import MagicMock, Mock
import pytest

# Mock PySide6 modules before any imports that depend on them
sys.modules['PySide6'] = MagicMock()
sys.modules['PySide6.QtGui'] = MagicMock()
sys.modules['PySide6.QtWidgets'] = MagicMock()
sys.modules['PySide6.QtCore'] = MagicMock()
sys.modules['PySide6.QtCharts'] = MagicMock()


def pytest_sessionstart():
    pass


def pytest_runtest_setup(item):
    # called for running each test in 'a' directory
    print("setting up", item)


def pytest_sessionfinish():
    # called for running each test in 'a' directory
    print("ended")
    try:
        from runsit import MainClass
        MainClass.killallchilds(tolog=False)
    except:
        pass  # Ignore errors in cleanup
