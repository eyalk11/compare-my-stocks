from abc import ABCMeta, abstractmethod


class InputDataImplInterface(metaclass=ABCMeta):
    @classmethod
    @abstractmethod
    def full_data_load(self):
        pass

    @abstractmethod
    def load_cache(self, minimal, process_params):
        pass

    @abstractmethod
    def get_currency_factor_for_sym(self, sym):
        pass

    @abstractmethod
    def get_currency_for_sym(self, sym, real_one):
        pass

    @abstractmethod
    def save_data(self):
        pass
