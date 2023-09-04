import logging
import os
import sys

from config import config


class JupyterCommonHandler:
    def __int__(self):
        self.reason =None
    @staticmethod
    def resolve_voila(widg):
        if (os.path.basename(sys.executable).lower() in ['python.exe',
                                                             'python3.exe']) or config.Voila.VOILA_PYTHON_PROCESS_PATH is not None:
            return True

        if config.Voila.AUTO_RESOVLE_VOILA_PYTHON:
            import shutil
            widg.python_process_path=shutil.which('python.exe')
            if widg.python_process_path!= None:
                logging.warning(f'Auto-resolved voila process to {widg.python_process_path}')
                return True
        self.reason='Not using voila because of empty python config. \n run installvoila.bat , and fill in config.Voila.VOILA_PYTHON_PROCESS_PATH'
        logging.warning(self.reason)
        return False
