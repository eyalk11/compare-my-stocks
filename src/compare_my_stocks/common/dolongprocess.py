from functools import partial

from PySide6.QtCore import QObject, Signal, QThread


class DoLongProcess(QObject):
    finished = Signal()
    def __init__(self,task):
        QObject.__init__(self)
        self._task=task
        self._realtask=None
        self.started=False
        self.thread = QThread()
        self.moveToThread(self.thread)
        self.thread.started.connect(self.run)
        self.finished.connect(self.thread.quit)

    def run(self):
        self.started = True
        print('bef real task')
        self._realtask()
        print('post')
        self.finished.emit()
        self.started = False


    @property
    def is_started(self):
        return self.started

    def startit(self,*params):

        self._realtask= partial(self._task,*params)

        #self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()