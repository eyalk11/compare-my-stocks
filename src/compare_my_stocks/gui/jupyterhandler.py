import logging
import os
import sys
import webbrowser
from enum import auto, IntEnum

import psutil
from PySide6.QtWidgets import QLabel, QVBoxLayout, QFrame

from common.simpleexceptioncontext import simple_exception_handling
from common.loghandler import TRACELEVEL
from config import config
from gui.jupytercommon import JupyterCommonHandler
from qtvoila import QtVoila
from gui.forminterface  import FormInterface
from common.dolongprocess import DoLongProcessSlots, TaskParams


class State(IntEnum):
    UNINITALIZED=auto()
    LOADING=auto()
    RUNNING=auto()


class JupyterHandler(FormInterface, JupyterCommonHandler):


    def __init__(self):
        self.voila_run=State.UNINITALIZED

        self.last_file_name=None
        self.file_name =None
        self._voila_task = DoLongProcessSlots(self.generation_task)
        self._wont_run=False
        self.reason=None
        #make wont_run a property
    @property
    def wont_run(self):
        return self._wont_run

    @wont_run.setter
    def wont_run(self,value):


        if value and self._wont_run==False:
            self.locate_label_over_voila()
        self._wont_run = value
    def locate_label_over_voila(self):

        # Create the label that we want to place inside the frame
        new_label = QLabel('''
        Here should have been your jupyter notebook, with real time analysis of the data. 
        
        However, something didn't quite work out :( 
        Please check the log for more information.
        
        On clean install, you may want to run install\installvoila.bat that installs python and the voila package (Needed to display the notebook).
        '''+ f"\nThe reason seems to be:\n { self.reason}" if self.reason is not None else "")

        # Create a QFrame to hold the new label
        frame = QFrame()
        # Set the frame's border style for visibility during testing
        frame.setFrameStyle(QFrame.Box)

        # Create a layout for the frame and add the new label to it
        frame_layout = QVBoxLayout()
        frame_layout.addWidget(new_label)
        frame.setLayout(frame_layout)

        # Replace the original widget with the frame
        self.window.note_group.layout().replaceWidget( self.window.voila_widget, frame)







    def voila_loaded(self,k):
        if k==-1:
            self.reason="Major issue with voila. wasn't load."
            logging.error(self.reason)
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

        if self.window.note_group.isHidden():
            return

        if self.wont_run:
            return
        #self.generation_task()
        self._voila_task.command.emit(TaskParams(params=tuple()))

    def reload_me(self):
        #self.finished_generation(2)
        self.window.voila_widget.refresh()


    @simple_exception_handling("Generation task")
    def generation_task(self):
        self.window.voila_widget: QtVoila
        self.window.voila_widget.max_voila_wait = config.Voila.MaxVoilaWait

        self.window.voila_widget: QtVoila
        if not self.generate_temp():
            return
        self.window.voila_widget.external_notebook = config.File.DefaultNotebook
        if self.window.voila_widget.python_process_path is None:
            self.window.voila_widget.python_process_path = config.Voila.VoilaPythonProcessPath
            self.wont_run = not self.resolve_voila(self.window.voila_widget)
        if self.wont_run:
            return
        open(config.File.DataFilePtr, 'wt').write(self.file_name)
        if self.voila_run == State.UNINITALIZED:
            if not config.Voila.DontRunNotebook:
                self.voila_run = State.LOADING
                self.window.voila_widget.run_voila()
        elif self.voila_run == State.RUNNING:
            self.voila_run = State.LOADING
            self.window.voila_widget.close_renderer()
            self.window.voila_widget.run_voila()

    def remove_file(self):
        if self.file_name!=None:
            try:
                os.remove(self.file_name)
            except:
                logging.debug(('error removing tmp'))
                return False

    def generate_temp(self):
        import tempfile
        self.remove_file()

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            name = tmp.name
            import pickle
            pickle.dump(self.graphObj.serialized_data(), tmp)
        self.file_name= name
        return True

    @simple_exception_handling("launch notebook")
    def launch_notebook(self,filename=None):
        if filename==None:
            filename=config.File.DefaultNotebook

        from notebook.notebookapp import list_running_servers
        pids = {x['pid']:x for x in list_running_servers()}

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
