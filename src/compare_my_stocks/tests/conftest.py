# Pydantic 2 + PySide6 import-hook cycle:
#   compare_my_stocks/__init__.py imports runsit -> PySide6 -> shibokensupport,
#   which installs an import hook that calls inspect.getsource on every newly
#   loaded module. inspect.getsource probes `__wrapped__` via hasattr, which
#   triggers pydantic's module-level __getattr__ (the v1->v2 migration shim).
#   The shim itself does `from ._internal._validators import import_string`,
#   re-entering pydantic mid-import → circular ImportError on _validators.
#
# Fix: short-circuit pydantic's __getattr__ for dunder names so hasattr probes
# don't trigger the migration shim. Pydantic never exports dunders via the
# shim, so this is safe. Apply it as the very first thing in conftest, before
# `import config` triggers PySide6 / pydantic loading.
def _patch_pydantic_dunder_getattr():
    import sys
    if 'pydantic' in sys.modules:
        return
    import pydantic as _p
    _orig = _p.__getattr__
    def _safe_getattr(name):
        if name.startswith('__') and name.endswith('__'):
            raise AttributeError(name)
        return _orig(name)
    _p.__getattr__ = _safe_getattr
_patch_pydantic_dunder_getattr()

import config as _cfg
_cfg.config.Sources.IBSource.PromptOnConnectionFail = False
_cfg.config.TransactionHandlers.IB.PromptOnQueryFail = False


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

def mock_pside():
    import sys
    from unittest.mock import MagicMock, Mock
    import pytest
    
    # Mock PySide6 modules before any imports that depend on them
    sys.modules['PySide6'] = MagicMock()
    sys.modules['PySide6.QtGui'] = MagicMock()
    sys.modules['PySide6.QtWidgets'] = MagicMock()
    sys.modules['PySide6.QtCore'] = MagicMock()
    sys.modules['PySide6.QtCharts'] = MagicMock()

