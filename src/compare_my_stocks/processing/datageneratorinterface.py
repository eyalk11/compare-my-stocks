from abc import ABCMeta, abstractmethod


class DataGeneratorInterface(metaclass=ABCMeta):
    @abstractmethod
    def generate_data(self):
        pass

    @abstractmethod
    def serialized_data(self):
        pass

