USEWX=0
USEWEB=0
USEQT=1
import sys

try:
    import config
except:
    print('please rename exampleconfig to config and adjust accordingly')
    sys.exit(1)


from enum import Flag, auto, Enum


class Types(Flag):
    PRICE=1
    VALUE=auto()
    PROFIT = auto()
    TOTPROFIT = auto()
    RELPROFIT = auto()
    THEORTICAL_PROFIT=auto()
    ABS= auto()
    RELTOMAX=auto()
    PRECENTAGE=auto()
    DIFF=auto()
    COMPARE=auto()


class UseCache(Enum):
    DONT=0
    USEIFAVALIABLE=1
    FORCEUSE=2


class UniteType(Flag):
    NONE=0
    SUM=auto()
    AVG=auto()
    ADDTOTAL=auto()