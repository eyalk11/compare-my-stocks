import dataclasses
import json
import logging

from PySide6.QtWidgets import QInputDialog, QLineEdit

from common.common import EnhancedJSONEncoder
from config import config
from engine.parameters import Parameters, copyit
from gui.forminitializerinterface import FormInitializerInterface
from gui.formobserverinterface import FormObserverInterface, ResetRanges

# Fields that are transient control flags, not part of the saved graph
# definition. Stripped on save and ignored on load so the on-disk JSON
# stays stable across UI sessions.
_TRANSIENT_PARAM_FIELDS = ('reset_ranges',)


class GraphsHandler(FormObserverInterface, FormInitializerInterface):
    def __init__(self):
        self.graphs = {}
        self.lastgraphtext = ""

    def load_existing_graphs(self):
        try:
            # gg=Deserializer(open(config.File.GraphFN,'rt'))
            gg = json.load(open(config.File.GraphFN, 'rt'))  # ,object_hook=Deserializer
            for v in gg.values():
                for k in _TRANSIENT_PARAM_FIELDS:
                    v.pop(k, None)
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
        logging.info(f"GUI internal_save: text={text!r} upd={upd}")
        self.graphs[text] = copyit(self.graphObj.params)
        if upd:
            self.lastgraphtext = text

        serializable = {}
        for name, params in self.graphs.items():
            d = dataclasses.asdict(params)
            for k in _TRANSIENT_PARAM_FIELDS:
                d.pop(k, None)
            serializable[name] = d
        open(config.File.GraphFN, 'wt').write(json.dumps(serializable, cls=EnhancedJSONEncoder))
        self.update_graph_list()

    def load_graph(self, text=None):
        logging.info(f"GUI load_graph: text={text!r}")
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication

        # Hard-block compare_changed for the full duration of the load:
        # both blockSignals AND ignore_updates_for_now have proven racy
        # here — editable combos re-emit currentIndexChanged via the inner
        # QLineEdit after both guards are released. Use a dedicated flag
        # that compare_changed checks, released only after the Qt event
        # loop has had a chance to drain queued signals.
        self._loading_graph = True
        wc = self.window.comparebox

        def release():
            self._loading_graph = False
            logging.debug("GUI load_graph: _loading_graph released")

        def after_task():
            logging.info(f"GUI load_graph after_task: ext={self.graphObj.params.ext} groups={self.graphObj.params.groups} cur_cat={self.graphObj.params.cur_category!r}")
            self.setup_controls_from_params(0, 1)
            self.update_graph(ResetRanges.FORCE,
                              force=True)  # There is a bug of the graph not fitting in screen. This solves it.
            # Flush queued events (deferred currentIndexChanged from the
            # editable combo's inner QLineEdit will land here), THEN
            # release the flag on the next event-loop tick.
            QApplication.processEvents()
            QTimer.singleShot(0, release)

        try:
            if text == None:
                if not self.window.graphList.currentItem():
                    release()
                    return
                text = self.window.graphList.currentItem().text()
            if text not in self.graphs:
                logging.warn(f'graph {text} not found')
                release()
                return
            # Also block at the widget level for the synchronous portion.
            wc.blockSignals(True)
            try:
                self.graphObj.params = copyit(self.graphs[text])
                self.update_graph(ResetRanges.FORCE, force=True, after=after_task)
            finally:
                wc.blockSignals(False)
            # should wait after update with controls -> after_task

        except:
            import traceback;
            traceback.print_exc()
            logging.debug(('failed loading graph'))
            release()

    def save_last_graph(self):
        if config.Running.LastGraphName:
            self.internal_save(config.Running.LastGraphName, upd=False)

    def load_last_if_needed(self):
        if config.Running.LoadLastAtBegin:
            self.load_graph(config.Running.LastGraphName)
        return config.Running.LoadLastAtBegin
