import logging
import os
import sys
import webbrowser

import psutil

from common.loghandler import TRACELEVEL
from config import config
from qtvoila import QtVoila
from gui.forminterface  import FormInterface
from common.dolongprocess import DoLongProcessSlots

class JupyterHandler(FormInterface):


    def __init__(self):
        self.voila_run=False
        self.already_running=False

        self.last_file_name=None
        self.file_name =None
        self._voila_task = DoLongProcessSlots(self.generation_task)

    def load_jupyter_observers(self):
        self.graphObj.finishedGeneration.connect(self.finished_generation)
        self.window.debug_btn.pressed.connect(self.launch_notebook)
        self.window.reload_notebook.pressed.connect( self.window.voila_widget.reload)

    def finished_generation(self,number):
        if self.already_running:
            logging.log(TRACELEVEL,('already'))
            return
        if self.window.note_group.isHidden():
            return
        self.generation_task()
        #self._voila_task.command.emit(tuple())

    def generation_task(self):
        self.window.voila_widget: QtVoila
        self.already_running=True
        if not self.generate_temp():
            return
        self.window.voila_widget.external_notebook = config.DEFAULTNOTEBOOK
        open(config.DATAFILEPTR,'wt').write(self.file_name)
        if not self.voila_run:
            if not config.DONT_RUN_NOTEBOOK:
                self.window.voila_widget.run_voila()
            self.voila_run=True
        else:
            self.window.voila_widget.reload()

        self.already_running = False

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
            cmd = [sys.executable, '-m', 'notebook', filename]
            subprocess.Popen(cmd,stderr=subprocess.PIPE,stdout=subprocess.PIPE)
