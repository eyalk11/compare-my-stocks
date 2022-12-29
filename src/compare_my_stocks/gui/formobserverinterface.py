from enum import Enum

from gui.forminterface import FormInterface


class ResetRanges(int,Enum):
    DONT=0
    IfAPROP=1
    FORCE=2

class FormObserverInterface(FormInterface):
    def update_graph(self, reset_ranges : ResetRanges, force=False, after=None,adjust_date=False):
        ...

