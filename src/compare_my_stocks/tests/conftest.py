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
    # Short-circuit dunder lookups in pydantic's migration shim so shiboken's
    # import-hook probes (hasattr(f, '__wrapped__'), etc.) don't re-enter
    # pydantic mid-import and trigger a circular ImportError. Patches
    # `getattr_migration` itself so every submodule (`pydantic.errors`,
    # `pydantic.config`, ...) that uses it is covered, not just the top-level
    # package.
    import sys
    if 'pydantic' in sys.modules:
        return
    try:
        from pydantic import _migration
        _orig = _migration.getattr_migration
    except (ImportError, AttributeError):
        return  # pydantic v1 or layout changed; nothing to patch
    def _safe_getattr_migration(module):
        wrapper = _orig(module)
        def _safe(name):
            if name.startswith('__') and name.endswith('__'):
                raise AttributeError(name)
            return wrapper(name)
        return _safe
    _migration.getattr_migration = _safe_getattr_migration
    # Top-level pydantic has its own custom __getattr__ (not a migration
    # wrapper), so wrap it instead of replacing it: only short-circuit dunders,
    # delegate everything else to the original.
    import pydantic as _p
    if hasattr(_p, '__getattr__'):
        _p_orig = _p.__getattr__
        def _safe_p_getattr(name, _orig=_p_orig):
            if name.startswith('__') and name.endswith('__'):
                raise AttributeError(name)
            return _orig(name)
        _p.__getattr__ = _safe_p_getattr
_patch_pydantic_dunder_getattr()

import pytest as _pytest


@_pytest.fixture(scope="session")
def _qcoreapp_session():
    """Singleton QCoreApplication for the whole test session."""
    from PySide6.QtCore import QCoreApplication
    import sys
    app = QCoreApplication.instance() or QCoreApplication(sys.argv or ['pytest'])
    yield app
    app.processEvents()


@_pytest.fixture
def qcoreapp(_qcoreapp_session):
    """Opt-in QCoreApplication for tests that build Qt objects (QSemaphore,
    QThread, signals) without going through the GUI. Without one, those
    objects warn ("QEventLoop: Cannot be used without QApplication") and Qt
    crashes the interpreter on GC (STATUS_STACK_BUFFER_OVERRUN on Windows).
    Function-scoped so each test drains pending events on teardown — without
    that, leaked QSemaphores from earlier tests get destructed mid-next-test
    and corrupt Qt internals."""
    yield _qcoreapp_session
    _qcoreapp_session.processEvents()


@_pytest.fixture(autouse=True)
def _qcoreapp_for_integration(request):
    # Integration tests construct real engine/input objects that pull in
    # QSemaphore/QThread; without a QCoreApplication the process crashes on
    # GC at session end (0xC0000409). Auto-apply the qcoreapp fixture only
    # for tests carrying the `integration` marker so unit tests stay free of
    # Qt setup.
    if request.node.get_closest_marker("integration"):
        request.getfixturevalue("qcoreapp")
    yield


import config as _cfg
_cfg.config.Sources.IBSource.PromptOnConnectionFail = False
_cfg.config.TransactionHandlers.IB.PromptOnQueryFail = False


def pytest_runtest_setup(item):
    # called for running each test in 'a' directory
    print("setting up", item)


def pytest_sessionfinish():
    # NOTE: do NOT call MainClass.killallchilds here. It calls
    # kill_proc_tree(os.getpid(), including_parent=True), which terminates the
    # pytest process with exit code 15 BEFORE pytest's terminal summary is
    # printed and BEFORE the actual test exit code is returned. If a real
    # ibsrv child needs killing, kill it explicitly instead.
    print("ended")
    try:
        from ib.remoteprocess import RemoteProcess
        proc = RemoteProcess()
        if getattr(proc, 'proc', None):
            try:
                from runsit import MainClass
                MainClass().kill_proc_tree(proc.proc.pid, including_parent=True)
            except Exception:
                pass
    except Exception:
        pass

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

