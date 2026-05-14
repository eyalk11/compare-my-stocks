"""PyQtGraph-based canvas widget that mirrors the small surface area of
the matplotlib `MplCanvas` used by `forminitializer.py`.

Exposes `.figure` and `.ax` attributes so the surrounding code can stay
agnostic of the rendering backend. `.ax` is the `pyqtgraph.PlotItem` that
the `GraphGenerator` draws into; `.figure` is the `GraphicsLayoutWidget`.
"""
from __future__ import annotations

import pyqtgraph as pg
from PySide6.QtWidgets import QSizePolicy

# Module-level — must run before any GraphicsLayoutWidget is constructed,
# otherwise pyqtgraph picks up its default black background.
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')
pg.setConfigOption('antialias', True)


class PyQtGraphCanvas(pg.GraphicsLayoutWidget):
    def __init__(self):
        super().__init__()
        self.setBackground('w')
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        date_axis = pg.DateAxisItem(orientation='bottom')
        self.plot_item: pg.PlotItem = self.addPlot(axisItems={'bottom': date_axis})
        self.plot_item.showGrid(x=True, y=True, alpha=0.3)
        self.plot_item.addLegend(offset=(10, 10))
        self.figure = self
        self.ax = self.plot_item
