import logging
import threading
from functools import partial


from PySide6.QtCore import QObject, Signal, QThread, Slot , QRecursiveMutex


from common.common import simple_exception_handling
from common.loghandler import TRACELEVEL
import colorlog

class DoLongProcess(QObject):
    finished = Signal()
    # def quit_thread(self):
    #     logging.debug(f'quit thread {self.thread}')
    #     self.thread.quit()
    def __init__(self,task):
        QObject.__init__(self)
        self._task=task
        self._realtask=None
        self.started=False
        self.thread = QThread()
        self._lock= threading.Lock()


        #self.finished.connect(self.quit_thread)

    @Slot()
    def run(self):
        if not self._realtask:
            logging.error("no real task")
            return
        self.started = True
        logging.log(TRACELEVEL,('bef real task'))
        self._realtask()
        logging.log(TRACELEVEL,('post'))
        self.finished.emit()
        self.started = False


    @property
    def is_started(self):
        return self.started



from collections import namedtuple
TaskParams=namedtuple("TaskParams","params finish_params", defaults=(None,None))

class DoLongProcessSlots(QObject):
    finished = Signal(tuple)
    command = Signal(TaskParams)
    def __init__(self, task):
        QObject.__init__(self)
        self._task = task
        self._realtask = None
        self.started = False
        self.thread = QThread()
        self.moveToThread(self.thread)
        self.command.connect(self.process_command)
        self.thread.start()
        self.mutex=QRecursiveMutex()
        self.command_waiting=0

        #self.thread.data_generated.connect(self.run)
        #self.finished.connect(self.thread.quit)

    # @Slot
    # def run(self):
    #     self.data_generated = True
    #     logging.debug(('bef real task'))
    #     self._realtask()
    #     logging.debug(('post'))
    #     self.finished.emit()
    #     self.data_generated = False

    @property
    def is_started(self):
        return self.started

    @Slot(tuple)
    def process_command(self, taskparams):
        #import asyncio
        # try:
        #     asyncio.get_event_loop()
        # except:
        #     loop = asyncio.new_event_loop()
        #     asyncio.set_event_loop(loop)
        #     from ib_insync import IB,util
        #     util.useQt('PySide6')

        realtask = simple_exception_handling(err_description="excpetion in real task",never_throw=True)(partial(self._task, *taskparams.params))
        self.started = True
        self.mutex.lock()
        try:
            logging.log(TRACELEVEL,('bef real task long'))
            realtask()
            logging.log(TRACELEVEL,('post long'))

            #to update status
        finally:
            self.mutex.unlock()
        if taskparams.finish_params:
            self.finished.emit(taskparams.finish_params)
        else:
            self.finished.emit([])
        self.started = False

        # self.thread.finished.connect(self.thread.deleteLater)



