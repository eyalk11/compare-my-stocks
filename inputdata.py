from abc import ABC, abstractmethod


class InputData(ABC):
        @property
        @abstractmethod
        def tot_profit_by_stock(self):
            ...
        def value(self):
            ...
        @property
        @abstractmethod
        def alldates(self):
            ...
        @property
        @abstractmethod
        def holding_by_stock(self):
            ...
        @property
        @abstractmethod
        def rel_profit_by_stock(self):
            ...
        @property
        @abstractmethod
        def unrel_profit(self):
            ...
        @property
        @abstractmethod
        def avg_cost_by_stock(self):
            ...

