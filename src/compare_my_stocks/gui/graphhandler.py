import json
import logging

from PySide6.QtWidgets import QInputDialog, QLineEdit

from common.common import EnhancedJSONEncoder
from config import config
from engine.parameters import Parameters, copyit
from gui.forminitializerinterface import FormInitializerInterface
from gui.formobserverinterface import FormObserverInterface, ResetRanges


class GraphsHandler(FormObserverInterface, FormInitializerInterface):
    def __init__(self):
        self.graphs = {}
        self.lastgraphtext = ""

    def load_existing_graphs(self):
        try:
            # gg=Deserializer(open(config.File.GRAPHFN,'rt'))
            gg = json.load(open(config.File.GRAPHFN, 'rt'))  # ,object_hook=Deserializer
            self.graphs = {k: Parameters.load_from_json_dict(v) for k, v in gg.items()}
            self.update_graph_list()
        except:
            import traceback;
            traceback.print_exc()
            logging.warn(('err loading graphs'))
            return

    def update_graph_list(self):
        self.window.graphList.clear()
        self.window.graphList.addItems(list(self.graphs.keys()), )

    def save_graph(self):
        text, ok = QInputDialog().getText(self, "Enter Graph Name",
                                          "Graph name:", QLineEdit.Normal,
                                          self.lastgraphtext)
        if ok and text:
            self.internal_save(text)

    def internal_save(self, text, upd=True):
        self.graphs[text] = copyit(self.graphObj.params)
        if upd:
            self.lastgraphtext = text

        open(config.File.GRAPHFN, 'wt').write(json.dumps(self.graphs, cls=EnhancedJSONEncoder))
        self.update_graph_list()

    def load_graph(self, text=None):
        def after_task():
            self.setup_controls_from_params(0, 1)
            self.update_graph(ResetRanges.FORCE,
                              force=True)  # There is a bug of the graph not fitting in screen. This solves it.

        try:
            if text == None:
                if not self.window.graphList.currentItem():
                    return
                text = self.window.graphList.currentItem().text()
            if text not in self.graphs:
                logging.warn(f'graph {text} not found')
                return
            self.graphObj.params = copyit(self.graphs[text])
            self.update_graph(ResetRanges.FORCE, force=True, after=after_task)
            # should wait after update with controls -> after_task

        except:
            import traceback;
            traceback.print_exc()
            logging.debug(('failed loading graph'))

    def save_last_graph(self):
        if config.Running.LASTGRAPHNAME:
            self.internal_save(config.Running.LASTGRAPHNAME, upd=False)

    def load_last_if_needed(self):
        if config.Running.LOADLASTATBEGIN:
            self.load_graph(config.Running.LASTGRAPHNAME)
        return config.Running.LOADLASTATBEGIN
