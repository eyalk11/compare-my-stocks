from enum import Enum


class ResetRanges(int,Enum):
    DONT=0
    IfAPROP=1
    FORCE=2