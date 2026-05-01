import sys
import multiprocessing
multiprocessing.freeze_support()
from contextvars import ContextVar
ContextVar('context').set('main')

if 'ipykernel_launcher' in sys.argv:
    print(('strangeeee'))
    if sys.path[0] == '':
        del sys.path[0]

    from ipykernel import kernelapp as app
    app.launch_new_instance()

    sys.exit(0)

#cheating...
try:
    __builtins__['SILENT']=False
except:
    pass
#cheating...
try:
    __builtins__.SILENT=False
except:
    pass



from compare_my_stocks import MainClass
import subprocess


def _check_single_instance():
    import sys
    import ctypes
    _MUTEX_NAME = "Global\\CompareMyStocks_SingleInstance"
    _ERROR_ALREADY_EXISTS = 183
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _mutex = kernel32.CreateMutexW(None, False, _MUTEX_NAME)
    if ctypes.get_last_error() == _ERROR_ALREADY_EXISTS:
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox
            _app = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.warning(None, "Already Running",
                                "Compare My Stocks is already running.\n"
                                "Only one instance is allowed at a time.")
        except Exception:
            print("Compare My Stocks is already running. Only one instance is allowed.", flush=True)
        sys.exit(1)
    # Keep _mutex referenced so it is not GC'd before the process exits
    _check_single_instance._mutex = _mutex


if __name__ == "__main__":
    import argparse

    # Create the parser
    parser = argparse.ArgumentParser()
    # Add the console switch
    parser.add_argument('--console', action='store_true', help='Enable console')
    parser.add_argument('--noconsole', action='store_true', help='Disable console anyway')
    # Add the ibconsole switch
    parser.add_argument('--ibconsole', action='store_true', help='Enable ibconsole')
    parser.add_argument('--debug', action='store_true', help='Enable debug')
    parser.add_argument('--ibsrv', action='store_true', help='Use ibsrv instead')
    parser.add_argument('--nogui', action='store_true', help='Run without GUI')
    parser.add_argument('--noprompt', action='store_true', help='Disable interactive prompts (e.g. IB Flex token failure)')
    parser.add_argument('--config-file', dest='config_file', default=None,
                        help='Absolute path to a myconfig.yaml to use instead of the default. '
                             'Overrides COMPARE_STOCK_CONFIG_FILE env var.')
    # Parse the command-line arguments
    args = parser.parse_args()

    if args.config_file:
        import os
        os.environ['COMPARE_STOCK_CONFIG_FILE'] = os.path.abspath(os.path.expanduser(args.config_file))

    if args.ibsrv:
        from compare_my_stocks import ibsrv
    else:
        _check_single_instance()
        MainClass().main(args.console,args.ibconsole,args.debug,args.noconsole,args.nogui,args.noprompt)
