from abc import abstractmethod

from engine.compareengineinterface import CompareEngineInterface
from engine.symbolsinterface import SymbolsInterface


class FormInterface:
        @property
        @abstractmethod
        def window(self):
            ...

        @property
        @abstractmethod
        def graphObj(self) -> CompareEngineInterface:
            ...

