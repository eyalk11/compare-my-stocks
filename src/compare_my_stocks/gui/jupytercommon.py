import logging
import os
import sys

from config import config


class JupyterCommonHandler:
    def __int__(self):
        self.reason =None
    @staticmethod
    def resolve_voila():
        logging.debug('resolve_voila: starting resolution')

        logging.debug(f'resolve_voila: checking config.Voila.VoilaPythonProcessPath={config.Voila.VoilaPythonProcessPath!r}')
        if config.Voila.VoilaPythonProcessPath is not None:
            logging.info(f'resolve_voila: using configured VoilaPythonProcessPath -> {config.Voila.VoilaPythonProcessPath}')
            return True, config.Voila.VoilaPythonProcessPath

        logging.debug(f'resolve_voila: checking sys.executable={sys.executable!r}')
        if os.path.basename(sys.executable).lower() in ['python.exe', 'python3.exe']:
            logging.debug('resolve_voila: local python detected, attempting to import voila')
            try:
                import voila  # noqa: F401
                logging.info(f'resolve_voila: voila importable in local python -> {sys.executable}')
                return True, None 
            except ImportError:
                logging.warning('resolve_voila: local python detected but voila is not importable; falling back.')
        else:
            logging.debug('resolve_voila: sys.executable is not a plain python.exe (likely frozen), skipping local-import check')

        logging.debug(f'resolve_voila: checking config.Voila.AutoResovleVoilaPython={config.Voila.AutoResovleVoilaPython}')
        if config.Voila.AutoResovleVoilaPython:
            localappdata = os.environ.get('LOCALAPPDATA')
            logging.debug(f'resolve_voila: LOCALAPPDATA={localappdata!r}')
            if localappdata:
                candidate = os.path.join(localappdata, 'compare-my-stocks', 'venv', 'Scripts', 'python.exe')
                logging.debug(f'resolve_voila: probing LOCALAPPDATA candidate {candidate}')
                if os.path.isfile(candidate):
                    logging.warning(f'resolve_voila: auto-resolved voila process to {candidate}')
                    return True, candidate
                else:
                    logging.debug('resolve_voila: LOCALAPPDATA candidate not found')

            import shutil
            candidate = shutil.which('python.exe')
            logging.debug(f'resolve_voila: shutil.which(python.exe)={candidate!r}')
            if candidate is not None:
                logging.warning(f'resolve_voila: auto-resolved voila process to {candidate}')
                return True, candidate
        else:
            logging.debug('resolve_voila: AutoResovleVoilaPython disabled, skipping auto-resolution')

        reason = 'Not using voila because of empty python config. \n run installvoila.bat , and fill in config.Voila.VOILA_PYTHON_PROCESS_PATH'
        logging.warning(reason)
        return False, None
