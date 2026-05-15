import logging
import os  # This Python file uses the following encoding: utf-8
from pathlib import Path
import sys
from PySide6 import QtCore
import PySide6
from PySide6.QtWidgets import QMainWindow, QLabel
from PySide6.QtCore import QFile, QTimer, QEvent
from PySide6.QtUiTools import QUiLoader
from superqt.sliders._labeled import EdgeLabelMode
from superqt import QLabeledRangeSlider
from PySide6 import QtGui

from common.autoreloader import ModuleReloader
from qtvoila import QtVoila

from engine.symbolsinterface import SymbolsInterface
from gui.daterangeslider import QDateRangeSlider
from gui.forminitializer import FormInitializer
from qt_collapsible_section import Section

try:
    from config import config
except Exception as e :
    logging.debug(('please set a config file'))
    sys.exit(1)


from superqt import QLabeledDoubleRangeSlider

from six import with_metaclass

class MainWindow(FormInitializer,QMainWindow):

    def __init__(self):
        QMainWindow.__init__(self)
        FormInitializer.__init__(self)
        self.load_ui()
        self._modreloader= ModuleReloader()


    def closeEvent(self, event):
        self.remove_file()
        self.wind.voila_widget.close_renderer()


    @property
    def graphObj(self) -> SymbolsInterface:
        return self._graphObj

    @graphObj.setter
    def graphObj(self, value):
        self._graphObj = value

    def load_ui(self):
        # Handle high resolution displays:
        loader = QUiLoader()
        loader.registerCustomWidget(QDateRangeSlider)
        loader.registerCustomWidget(QLabeledRangeSlider)
        loader.registerCustomWidget(QLabeledDoubleRangeSlider)
        loader.registerCustomWidget(QtVoila)
        loader.registerCustomWidget(Section)
        path = os.fspath(Path(__file__).resolve().parent / "mainwindow.ui")
        iconpath = os.fspath(Path(__file__).resolve().parent / "icon.ico")

        ui_file = QFile(path)
        ui_file.open(QFile.ReadOnly)

        self.wind= loader.load(ui_file, None)
        self.wind.closeEvent= self.closeEvent
        ui_file.close()
        self.setCentralWidget(self.wind)

        self.setWindowIcon(QtGui.QIcon(iconpath))
        self.setWindowTitle(config.Running.Title)
        if os.name == 'nt':
            # This is needed to display the app icon on the taskbar on Windows 7
            import ctypes
            myappid = 'MyOrganization.MyGui.1.0.0' # arbitrary string
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        self.wind.configure_btn.clicked.connect(self._open_config_editor)
        self._setup_status_bar()
        self.after_load()

    # ------------------------------------------------------------------
    # Status bar: shows IB connection + which API keys are configured.
    # Auto-hides ~4s after startup; reappears when the cursor hovers near
    # the bottom edge of the window.
    # ------------------------------------------------------------------
    def _setup_status_bar(self):
        sb = self.statusBar()
        sb.setSizeGripEnabled(False)
        self._sb_labels = {}
        for key, caption in [
            ("IB", "IB"),
            ("Flex", "Flex"),
            ("StockPrices", "RAPID StockPrices"),
            ("SeekingAlpha", "RAPID SeekingAlpha"),
            ("RapidYFinance", "RAPID YFinance"),
            ("Polygon", "Polygon"),
        ]:
            lbl = QLabel()
            lbl.setProperty("caption", caption)
            lbl.setContentsMargins(6, 0, 6, 0)
            # addWidget (not addPermanentWidget) anchors to the LEFT side of
            # the status bar so users see connection state immediately.
            sb.addWidget(lbl)
            self._sb_labels[key] = lbl
        # Hint shown only when at least one indicator is red — tells the
        # user where to go to fix it.
        self._sb_hint = QLabel(
            "<b>⚠ Select <i>Edit Config</i> → <i>Help</i> to fix</b>"
        )
        self._sb_hint.setStyleSheet(
            "color: #c62828; padding: 1px 8px;"
        )
        self._sb_hint.setVisible(False)
        sb.addWidget(self._sb_hint)
        self._refresh_status()

        self._sb_refresh = QTimer(self)
        self._sb_refresh.setInterval(2000)
        self._sb_refresh.timeout.connect(self._refresh_status)
        self._sb_refresh.start()

        self._sb_hide = QTimer(self)
        self._sb_hide.setSingleShot(True)
        self._sb_hide.timeout.connect(sb.hide)
        self._sb_hide.start(4000)

        # Poll cursor position; show status bar when near the bottom edge.
        # Cheaper than installing a global event filter, and works even
        # when the bar is hidden (event filters on a hidden widget don't
        # see mouse moves into its old area).
        self._sb_hover = QTimer(self)
        self._sb_hover.setInterval(300)
        self._sb_hover.timeout.connect(self._check_status_hover)
        self._sb_hover.start()

    def _check_status_hover(self):
        if not self.isVisible():
            return
        local = self.mapFromGlobal(QtGui.QCursor.pos())
        if 0 <= local.x() <= self.width() and \
                self.height() - 24 <= local.y() <= self.height():
            sb = self.statusBar()
            if not sb.isVisible():
                sb.show()
            # Each hover keeps it up another 3s past the last hover.
            self._sb_hide.start(3000)

    def _refresh_status(self):
        try:
            ib_ok = self._is_ib_connected()
        except Exception:
            ib_ok = False
        keys = self._configured_api_keys()
        states = {
            "IB": ib_ok,
            "Flex": keys["Flex"],
            "StockPrices": keys["StockPrices"],
            "SeekingAlpha": keys["SeekingAlpha"],
            "RapidYFinance": keys["RapidYFinance"],
            "Polygon": keys["Polygon"],
        }
        self._set_label("IB", "IB", states["IB"], ok_text="connected", bad_text="down")
        self._set_label("Flex", "Flex", states["Flex"])
        self._set_label("StockPrices", "RAPID StockPrices", states["StockPrices"])
        self._set_label("SeekingAlpha", "RAPID SeekingAlpha", states["SeekingAlpha"])
        self._set_label("RapidYFinance", "RAPID YFinance", states["RapidYFinance"])
        self._set_label("Polygon", "Polygon", states["Polygon"])
        if getattr(self, "_sb_hint", None) is not None:
            self._sb_hint.setVisible(not all(states.values()))

    def _set_label(self, key, caption, ok, ok_text="set", bad_text="missing"):
        lbl = self._sb_labels.get(key)
        if lbl is None:
            return
        colour = "#2e7d32" if ok else "#c62828"  # green / red
        lbl.setText(f"{caption}: {ok_text if ok else bad_text}")
        lbl.setStyleSheet(
            f"color: white; background: {colour}; "
            f"border-radius: 3px; padding: 1px 6px;"
        )

    def _is_ib_connected(self):
        eng = getattr(self, "_graphObj", None)
        inp = getattr(eng, "input_processor", None) if eng is not None else None
        src = getattr(inp, "_inputsource", None) if inp is not None else None
        return bool(getattr(src, "connected", False))

    @staticmethod
    def _configured_api_keys():
        def has(s):
            return bool(s and str(s).strip())
        return {
            "Flex": has(getattr(getattr(config.TransactionHandlers, "IB", None), "FlexToken", None)),
            "StockPrices": has(getattr(config.StockPricesHeaders, "X_RapidAPI_Key", None)),
            "SeekingAlpha": has(getattr(config.SeekingAlphaHeaders, "X_RapidAPI_Key", None)),
            "RapidYFinance": has(getattr(config.Jupyter, "RapidYFinanaceKey", None)),
            "Polygon": has(getattr(getattr(config.Sources, "PolySource", None), "Key", None)),
        }

    def _open_config_editor(self):
        from gui.config_gui import ConfigEditor, _default_config_path
        if getattr(self, "_cfg_editor", None) is None:
            self._cfg_editor = ConfigEditor(_default_config_path())
        self._cfg_editor.show()
        self._cfg_editor.raise_()
        self._cfg_editor.activateWindow()



    def run(self,graphObj : SymbolsInterface):
        self.graphObj = graphObj
        if self.graphObj==None:
            return

        self.prepare_sliders()
        self.setup_controls_from_params()
        self.setup_observers()

        self.showMaximized()
        if self.load_last_if_needed():
            self.update_graph(1)

        if  os.environ.get('PYCHARM_HOSTED') == '1':
            if config.Running.CheckReloadInterval ==0:
                return
            logging.debug("checking and reloading")
            timer = QTimer(self)
            timer.setInterval(1000* config.Running.CheckReloadInterval)
            timer.timeout.connect(self.check_reload)
            timer.start()

    def check_reload(self):
        #We check and reload all modules if they are changed, if we run on pycharm
        self._modreloader.check(True,True)

    #from PySide6.QtWidgets import QGroupBox
    #self.window.findChild(QGroupBox, name='graph_groupbox')
    #self.window.findChild(QGroupBox, name='graph_groupbox')
    def prepare_sliders(self):
        self.wind.max_num: QLabeledRangeSlider
        self.wind.max_num.setOrientation(PySide6.QtCore.Qt.Orientation.Horizontal)
        self.wind.max_num.setEdgeLabelMode(EdgeLabelMode.NoLabel)
        self.wind.min_crit : QLabeledDoubleRangeSlider
        self.wind.min_crit.setOrientation(PySide6.QtCore.Qt.Orientation.Horizontal)
        self.wind.min_crit.setEdgeLabelMode(EdgeLabelMode.NoLabel)
        self.wind.min_crit.update()
        #self.window.min_crit.label_shift_x = 10
        #self.window.max_num.label_shift_x = 10

        pass


