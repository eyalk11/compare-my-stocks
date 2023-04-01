import logging
import os
import sys
import webbrowser
from enum import Enum, auto, IntEnum

import psutil

from common.common import simple_exception_handling
from common.loghandler import TRACELEVEL
from config import config
from qtvoila import QtVoila
from gui.forminterface  import FormInterface
from common.dolongprocess import DoLongProcessSlots

class State(IntEnum):
    UNINITALIZED=auto()
    LOADING=auto()
    RUNNING=auto()

class JupyterHandler(FormInterface):


    def __init__(self):
        self.voila_run=State.UNINITALIZED
        self.in_generation=False

        self.last_file_name=None
        self.file_name =None
        self._voila_task = DoLongProcessSlots(self.generation_task)
        self.wont_run=False
        self.window.voila_widget :QtVoila


    def voila_loaded(self,k):
        if k==-1:
            logging.error("major issue with voila. wont loaded")
            self.wont_run=True
            self.voila_run = State.UNINITALIZED
            return
        logging.debug("Voila loaded")
        self.voila_run=State.RUNNING

    def load_jupyter_observers(self):
        self.graphObj.finishedGeneration.connect(self.finished_generation)
        self.window.debug_btn.pressed.connect(self.launch_notebook)
        self.window.reload_notebook.pressed.connect( self.reload_me)
        self.window.voila_widget.finished.connect(self.voila_loaded)

    def finished_generation(self,number):
        if self.in_generation:
            logging.log(TRACELEVEL,('already'))
            return
        if self.window.note_group.isHidden():
            return
        if self.wont_run:
            return
        self.generation_task()
        #self._voila_task.command.emit(tuple())

    def reload_me(self):
        self.voila_run = State.LOADING
        self.window.voila_widget.close_renderer()
        self.window.voila_widget.run_voila()

    @simple_exception_handling("Generation task")
    def generation_task(self):
        def resolve_voila():
            if (os.path.basename(sys.executable).lower() in ['python.exe',
                                                                 'python3.exe']) or config.VOILA_PYTHON_PROCESS_PATH is not None:
                return True

            if config.AUTO_RESOVLE_VOILA_PYTHON:
                import shutil
                self.window.voila_widget.python_process_path=shutil.which('python.exe')
                if self.window.voila_widget.python_process_path!= None:
                    logging.warning(f'Auto-resolved voila process to {self.window.voila_widget.python_process_path}')
                    return True
            logging.warning('Not using voila because of empty python config. \n run installvoila.bat , and fill in config.VOILA_PYTHON_PROCESS_PATH')
            return False

        self.window.voila_widget: QtVoila
        self.in_generation=True
        if not self.generate_temp():
            return
        self.window.voila_widget.external_notebook = config.DEFAULTNOTEBOOK
        if self.window.voila_widget.python_process_path is None:
            self.window.voila_widget.python_process_path = config.VOILA_PYTHON_PROCESS_PATH
            self.wont_run = not resolve_voila()
        if self.wont_run:
            return
        open(config.DATAFILEPTR,'wt').write(self.file_name)
        if self.voila_run==State.UNINITALIZED:
            if not config.DONT_RUN_NOTEBOOK:
                self.voila_run = State.LOADING
                self.window.voila_widget.run_voila()
        elif self.voila_run==State.RUNNING:
            self.reload_me()

        self.in_generation = False

    def generate_temp(self):
        import tempfile
        if self.file_name!=None:
            try:
                os.remove(self.file_name)
            except:
                logging.debug(('error tmp'))
                return False

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            name = tmp.name
            import pickle
            pickle.dump(self.graphObj.serialized_data(), tmp)
        self.file_name= name
        return True

    @simple_exception_handling("launch notebook")
    def launch_notebook(self,filename=None):
        if filename==None:
            filename=config.DEFAULTNOTEBOOK
        from nbmanager import api
        pids = {x['pid']:x for x in api.list_running_servers()}
        processes = list(filter(lambda p: p.pid in pids.keys(), psutil.process_iter()))
        dirname=os.path.dirname(filename)
        z=[ pids[p.pid]['url'] for p in processes if 'python' in p.name() and pids[p.pid]['notebook_dir']==dirname]

        if len(z)>0:
            logging.info(('launching existing session'))
            webbrowser.open(z[0])
        else:
            logging.info(('didn\'t find instance, running'))
            import subprocess
            cmd = ['start',sys.executable, '-m', 'notebook', filename]
            subprocess.Popen(cmd,stderr=subprocess.PIPE,stdout=subprocess.PIPE,shell=True)
