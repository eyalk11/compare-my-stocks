"""PyQtGraph-based canvas widget that mirrors the small surface area of
the matplotlib `MplCanvas` used by `forminitializer.py`.

Exposes `.figure` and `.ax` attributes so the surrounding code can stay
agnostic of the rendering backend. `.ax` is the `pyqtgraph.PlotItem` that
the `GraphGenerator` draws into; `.figure` is the `GraphicsLayoutWidget`.
"""
from __future__ import annotations

import datetime as _dt

import pyqtgraph as pg
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QSizePolicy

# Module-level — must run before any GraphicsLayoutWidget is constructed,
# otherwise pyqtgraph picks up its default black background.
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')
pg.setConfigOption('antialias', True)


class PyQtGraphCanvas(pg.GraphicsLayoutWidget):
    # Fires when the user zooms / pans the chart. Carries (start, end) as
    # naive Python datetimes (UTC; the axis uses utcOffset=0). Throttled
    # via SignalProxy so a mousewheel drag doesn't fire 60 times a second.
    xRangeChanged = Signal(object, object)

    def __init__(self):
        super().__init__()
        self.setBackground('w')
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        date_axis = pg.DateAxisItem(orientation='bottom', utcOffset=0)
        self.plot_item: pg.PlotItem = self.addPlot(axisItems={'bottom': date_axis})
        date_axis.setStyle(autoExpandTextSpace=True, autoReduceTextSpace=True)
        self.plot_item.showGrid(x=True, y=True, alpha=0.3)
        self.plot_item.addLegend(offset=(10, 10))
        self.figure = self
        self.ax = self.plot_item

        self._range_proxy = pg.SignalProxy(
            self.plot_item.vb.sigXRangeChanged,
            rateLimit=10,
            slot=self._emit_range,
        )

    def _emit_range(self, evt):
        import logging
        # SignalProxy forwards the original signal args directly:
        # sigXRangeChanged(viewbox, (xmin, xmax)) -> evt = (vb, (x0, x1)).
        try:
            _vb, (x0, x1) = evt
        except Exception as e:
            logging.debug(f"[chart-zoom] could not unpack range evt={evt!r}: {e}")
            return
        try:
            start = _dt.datetime.utcfromtimestamp(float(x0))
            end = _dt.datetime.utcfromtimestamp(float(x1))
        except (ValueError, OSError, OverflowError) as e:
            logging.debug(f"[chart-zoom] bad ts ({x0}, {x1}): {e}")
            return
        logging.debug(f"[chart-zoom] emit xRangeChanged {start}..{end}")
        self.xRangeChanged.emit(start, end)
