from abc import ABCMeta, abstractmethod


class FormInitializerInterface():
    @abstractmethod
    def prepare_graph_widget(self):
        pass

    @abstractmethod
    def after_load(self):
        pass

    @abstractmethod
    def set_all_toggled_value(self):
        pass

    @abstractmethod
    def setup_controls_from_params(self, initial, isinitialforstock):
        pass


    @abstractmethod
    def update_ranges(self, reset_type):
        pass