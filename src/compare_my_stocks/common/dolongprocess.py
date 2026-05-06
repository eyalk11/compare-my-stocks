import atexit
import logging
import threading
import weakref
from functools import partial


from PySide6.QtCore import QObject, Signal, QThread, Slot , QRecursiveMutex

from common.simpleexceptioncontext import simple_exception_handling
from common.loghandler import TRACELEVEL
import colorlog


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
        # Without this, an interpreter shutdown / GC of this object while the
        # OS thread is still running causes Qt to abort the process on Windows
        # ("QThread: Destroyed while thread '' is still running"). atexit runs
        # before the QApplication is torn down; the weakref keeps us from
        # pinning the object alive.
        _self_ref = weakref.ref(self)

        def _cleanup():
            obj = _self_ref()
            if obj is not None:
                obj.close()

        atexit.register(_cleanup)
        self._atexit_cleanup = _cleanup

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

    def close(self, timeout_ms=2000):
        """Stop the worker thread. Safe to call multiple times."""
        thread = getattr(self, "thread", None)
        if thread is None:
            return
        try:
            thread.quit()
            thread.wait(timeout_ms)
        except RuntimeError:
            # C++ side already gone (e.g. QApplication torn down before us).
            pass

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    @Slot(tuple)
    def process_command(self, taskparams):
        #import asyncio
        # try:
        #     asyncio.get_event_loop()
        # except:
        #     loop = asyncio.new_event_loop()
        #     asyncio.set_event_loop(loop)
        #     from ib_async import IB,util
        #     util.UseQT('PySide6')

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
                self.finished.emit(tuple())
            self.started = False

        # self.thread.finished.connect(self.thread.deleteLater)



