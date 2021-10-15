from abc import ABC, abstractmethod

USEWX=0
USEWEB=0
USEQT=1
import sys



from enum import Flag, auto, Enum


class Types(Flag):
    ABS = 0
    PRICE=auto()
    VALUE=auto()
    PROFIT = auto()
    TOTPROFIT = auto()
    RELPROFIT = auto()
    THEORTICAL_PROFIT=auto()

    RELTOMAX=auto()
    RELTOMIN=auto()
    RELTOSTART=auto()
    RELTOEND=auto()
    PRECENTAGE=auto()
    DIFF=auto()
    COMPARE=auto()
    PRECDIFF = PRECENTAGE | DIFF




class UseCache(Enum):
    DONT=0
    USEIFAVALIABLE=1
    FORCEUSE=2


class UniteType(Flag):
    NONE=0
    SUM=auto()
    AVG=auto()
    ADDTOTAL=auto()

class InputSourceType(Flag):
    Cache=0
    IB=auto()
    InvestPy=auto()


