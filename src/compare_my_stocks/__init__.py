import sys, os

if not getattr(sys, 'frozen', False):
    sys.path.insert(0,
        os.path.dirname(os.path.abspath(__file__)))

# from . import common
# from . import engine
# from . import input
# from . import gui
# from . import processing
# from . import graph
# from . import ib


#from . import config
try:
    from . import jupyter
    from .runsit import MainClass
except (ImportError, ModuleNotFoundError) as e:
    # Handle missing PySide6 or other GUI dependencies in headless/test environments
    if 'libEGL' in str(e) or 'PySide6' in str(e):
        import logging
        logging.debug(f"GUI dependencies not available: {e}")
        # Create stub MainClass for testing
        class MainClass:
            @staticmethod
            def killallchilds(tolog=False):
                pass
    else:
        raise
#from config import config
import logging
#import common

