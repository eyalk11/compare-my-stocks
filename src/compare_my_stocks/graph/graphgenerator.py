"""PyQtGraph-based GraphGenerator.

Replaces the previous matplotlib + mplcursors implementation. Public
surface is preserved (`active`, `gen_actual_graph`, `get_visible_cols`,
`show_hide`, `adjust_date`) so `engine.compareengine` and the GUI need
no changes beyond swapping the canvas widget.

Native hover annotation reproduces what mplcursors gave us: a vertical
reference line plus a tooltip listing every visible curve's interpolated
value at the cursor's x, with transaction details when the cursor is
near a scatter point.
"""
from __future__ import annotations

import logging
import math
import threading
from typing import Optional

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import (
    Qt, QPointF, QObject, QThread, QTimer, QCoreApplication,
    QMetaObject, Slot,
)
from PySide6.QtGui import QColor


def _run_on_gui_thread(fn):
    """Marshal `fn()` onto the GUI thread and wait for it to return.

    pyqtgraph creates QGraphicsItems / Qt timers that must be parented
    on the GUI thread. `gen_actual_graph` is called from a data-loader
    worker, so we hop threads here. Exceptions propagate back.
    """
    app = QCoreApplication.instance()
    if app is None or QThread.currentThread() == app.thread():
        return fn()

    done = threading.Event()
    result = [None, None]  # [value, exception]

    class _Invoker(QObject):
        def __init__(self):
            super().__init__()
            self.moveToThread(app.thread())

        def trigger(self):
            QMetaObject.invokeMethod(self, "_run", Qt.QueuedConnection)

        @Slot()
        def _run(self):
            try:
                result[0] = fn()
            except BaseException as e:  # noqa: BLE001
                result[1] = e
            finally:
                done.set()

    inv = _Invoker()
    inv.trigger()
    done.wait()
    if result[1] is not None:
        raise result[1]
    return result[0]

from common.common import Types, UniteType
from common.loghandler import TRACELEVEL
from common.simpleexceptioncontext import simple_exception_handling
from config import config
from engine.compareengineinterface import CompareEngineInterface


# ---------------------------------------------------------------------------
def _to_epoch(dt_index) -> np.ndarray:
    """Convert pandas DatetimeIndex / list of datetimes to UNIX seconds."""
    import pandas as pd
    idx = pd.DatetimeIndex(dt_index)
    if idx.tz is not None:
        idx = idx.tz_convert('UTC').tz_localize(None)
    return (idx.view('int64') // 1_000_000_000).astype('float64')


def _palette(n: int):
    base = [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
        '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
        '#393b79', '#637939', '#8c6d31', '#843c39', '#7b4173',
    ]
    return [base[i % len(base)] for i in range(n)]


def _round2(v):
    if v is None:
        return ''
    if isinstance(v, float) and math.isnan(v):
        return ''
    return f'{round(v, 2)}'


# ---------------------------------------------------------------------------
class GraphGenerator:
    """PyQtGraph-backed counterpart to the old matplotlib generator."""

    def __init__(self, eng: CompareEngineInterface, axes):
        """`axes` is the pyqtgraph PlotItem this generator draws into
        (analogous to the old matplotlib Axes). May be None for headless
        / --nogui mode."""
        self._eng = eng
        self._plot: Optional[pg.PlotItem] = axes
        self._curves: dict[str, pg.PlotDataItem] = {}
        self._curve_visible: dict[str, bool] = {}
        self._scatters: dict[str, pg.ScatterPlotItem] = {}
        self._tx_points: list[tuple[float, float, str]] = []
        self.last_stock_list: set = set()
        self.cur_shown_stock: set = set()
        self.adjust_date = False
        self.first_time = True
        self.orig_data = None
        self.additional_df = None
        self.typ = None
        self.unitetype = None
        self._hover_proxy = None
        self._vline: Optional[pg.InfiniteLine] = None
        self._tooltip: Optional[pg.TextItem] = None
        self._orig_epoch: Optional[np.ndarray] = None

    # ------------------------------------------------------------------
    @property
    def params(self):
        return self._eng.params

    @property
    def active(self) -> bool:
        return self._plot is not None

    # ------------------------------------------------------------------
    def get_visible_cols(self):
        return [n for n, v in self._curve_visible.items() if v]

    def show_hide(self, toshow):
        for name, curve in self._curves.items():
            curve.setVisible(bool(toshow))
            self._curve_visible[name] = bool(toshow)
        for sc in self._scatters.values():
            sc.setVisible(bool(toshow))

    # ------------------------------------------------------------------
    def get_title(self) -> str:
        type_ = self.params.type

        def rel(t):
            d = {
                Types.RELTOMAX: 'relative to maximum ',
                Types.RELTOMIN: 'relative to minimum ',
                Types.RELTOEND: 'relative to end ',
                Types.RELTOSTART: '' if t & Types.COMPARE else 'relative to start time ',
            }
            return d.get(t & (Types.RELTOSTART | Types.RELTOMAX | Types.RELTOMIN | Types.RELTOEND), '')

        def getbasetype(t):
            d = {
                Types.PROFIT: 'Unrealized profit',
                Types.VALUE: 'Value',
                Types.PRICE: 'Stock price',
                Types.TOTPROFIT: 'Total profit',
                Types.PERATIO: 'PE Ratio',
                Types.PRICESELLS: 'Price to sells',
                Types.THEORTICAL_PROFIT: 'Theortical profit',
                Types.RELPROFIT: 'Realized Profit',
            }
            return d.get(t & (
                Types.PROFIT | Types.VALUE | Types.PRICE | Types.RELPROFIT |
                Types.TOTPROFIT | Types.PERATIO | Types.PRICESELLS | Types.THEORTICAL_PROFIT),
                         d[Types.PRICE])

        lowerfirst = lambda s: s[0].lower() + s[1:]
        d = {
            Types.PRECENTAGE: lambda s: f'Percentage change {rel(type_)}of {lowerfirst(s)}',
            Types.PRECDIFF: lambda s: f'Percentage change difference {rel(type_)}of {lowerfirst(s)}',
            Types.DIFF: lambda s: f'Difference {rel(type_)}of {lowerfirst(s)}',
            Types.ABS: lambda s: s,
        }
        t = type_
        if ((t & Types.COMPARE) == 0) and t & (Types.PRECENTAGE | Types.DIFF):
            t = t & ~Types.DIFF
        basestr = d.get(t & (Types.PRECENTAGE | Types.PRECDIFF | Types.DIFF), d[Types.ABS])
        st = basestr(getbasetype(t))
        if t & Types.COMPARE and self.params.compare_with:
            st += ' compared with ' + self.params.compare_with
        return st

    # ------------------------------------------------------------------
    def _clear(self):
        if self._plot is None:
            return
        try:
            self._plot.legend.clear()
        except Exception:
            pass
        # Preserve the vline/tooltip across redraws; remove only data items.
        for item in list(self._curves.values()) + list(self._scatters.values()):
            self._plot.removeItem(item)
        self._curves.clear()
        self._curve_visible.clear()
        self._scatters.clear()
        self._tx_points = []

    # ------------------------------------------------------------------
    @simple_exception_handling("Error while generating graph",
                                err_to_ignore=[TypeError], always_throw=True)
    def gen_actual_graph(self, *args, **kwargs):
        return _run_on_gui_thread(lambda: self._gen_actual_graph(*args, **kwargs))

    def _gen_actual_graph(self, cols, dt, isline, starthidden, just_upd, type,
                          unitetype, orig_data, adjust_date=False,
                          plot_data=None, additional_df=None):
        if self._plot is None:
            return

        self.orig_data = orig_data
        self.additional_df = additional_df
        self.typ = type
        self.unitetype = unitetype

        self._clear()

        x = _to_epoch(dt.index)
        self._orig_epoch = _to_epoch(orig_data.index) if orig_data is not None else x

        colours = _palette(len(dt.columns))
        for col, colour in zip(dt.columns, colours):
            yv = dt[col].to_numpy(dtype='float64')
            mask = np.isfinite(yv)
            if not mask.any():
                continue
            curve = self._plot.plot(x[mask], yv[mask],
                                    pen=pg.mkPen(color=colour, width=2),
                                    name=col)
            self._curves[col] = curve
            self._curve_visible[col] = True

        self._plot.setTitle(self.get_title())

        if plot_data and self.params.show_transactions_graph:
            # Match matplotlib's `special` decision: snap markers to the
            # displayed line (instead of using raw cost) whenever the
            # y-axis is not the raw price — i.e. currency-adjusted price,
            # percentage, value, profit, etc. Otherwise the markers
            # sit at the historical transaction price and float far away
            # from the line the user is reading.
            special = bool(
                self.params.adjust_to_currency
                or self.params.adjusted_for_base_cur
                or not ((Types.PRICE & type) == Types.PRICE or type == Types.ABS)
            )
            self._plot_transactions(plot_data, colours, special=special)

        self._install_legend_toggles()
        self._install_hover()
        self._apply_shown_stock(starthidden, isline)

        self._plot.enableAutoRange(axis='y', enable=True)
        self.first_time = False

        try:
            logging.log(TRACELEVEL, '[gg] FINAL curves=%d visible=%d',
                        len(self._curves),
                        sum(1 for v in self._curve_visible.values() if v))
        except Exception:
            pass

    # ------------------------------------------------------------------
    def _plot_transactions(self, plot_data, colours, special=False):
        """Scatter each transaction at (date, price); circles for buys,
        squares for sells; size scales with |qty * cost| so bigger
        positions visually pop. Mirrors matplotlib generator's intent.

        When `special` is True (currency-adjusted / non-raw-price graphs),
        snap marker y to the displayed curve at the transaction's x via
        linear interpolation, so dots sit on the line rather than at the
        raw historical cost."""
        colour_by_sym = {sym: c for sym, c in zip(self._curves.keys(), colours)}

        # First pass: collect totals to derive a typical-size baseline
        # (so per-symbol scaling is comparable across symbols).
        all_totals = []
        for rows in plot_data.values():
            for entry in rows or ():
                _date, cost, qty, _src, _adj = entry
                if cost is None or qty is None:
                    continue
                if isinstance(cost, float) and math.isnan(cost):
                    continue
                all_totals.append(abs(qty * cost))
        if all_totals:
            arr = np.asarray(all_totals, dtype='float64')
            typical = float(np.average(arr))
            if arr.max() > 5 * typical:
                typical = float(arr.max()) / 2
            typical = max(typical, 1.0)
        else:
            typical = 1.0

        base_px = float(config.UI.CircleSize) * float(config.UI.CircleSizePercentage)
        base_px = max(8.0, base_px)  # don't disappear when config is tiny
        MIN_PX, MAX_PX = 6.0, 48.0

        for sym, rows in plot_data.items():
            if not rows:
                continue
            colour = colour_by_sym.get(sym, '#888888')
            spots = []
            shift_next_day = getattr(config.Input, 'TransactionsOnNextDay', False)
            for entry in rows:
                date, cost, qty, source, adj = entry
                if cost is None or (isinstance(cost, float) and math.isnan(cost)):
                    continue
                # Display-only shift: marker appears on the day after the
                # transaction so the value step visually follows it.
                display_date = (date + __import__('datetime').timedelta(days=1)
                                if shift_next_day else date)
                ts = float(_to_epoch([display_date])[0])
                if special and sym in self._curves:
                    xd, yd = self._curves[sym].getData()
                    if xd is not None and len(xd) > 0:
                        yv = float(np.interp(ts, xd, yd))
                    else:
                        yv = float(cost)
                else:
                    y = adj if adj is not None and not (isinstance(adj, float) and math.isnan(adj)) else cost
                    yv = float(y)
                if math.isnan(yv):
                    continue
                is_sell = qty is not None and qty < 0
                total = abs((qty or 0) * cost)
                size = base_px * math.sqrt(total / typical) if total > 0 else MIN_PX
                size = max(MIN_PX, min(MAX_PX, size))
                if is_sell:
                    # match matplotlib's area adjustment for square markers
                    size *= math.sqrt(math.pi / 4)

                def _adj_str(value, adjusted):
                    if adjusted:
                        return f'{_round2(value)} (adj. {_round2(adjusted)})'
                    return _round2(value)

                qty_adj = (qty * (cost / adj)) if (adj and qty is not None) else None
                tooltip = (
                    f'{sym}\n'
                    f'Date: {date.strftime("%Y-%m-%d %H:%M")}\n'
                    f'Cost: {_adj_str(cost, adj)}\n'
                    f'Qty: {_adj_str(qty, qty_adj)}\n'
                    f'Source: {source}'
                )

                spots.append({
                    'pos': (ts, yv),
                    'size': size,
                    'symbol': 's' if is_sell else 'o',
                    'brush': pg.mkBrush(QColor(colour)),
                    'pen': pg.mkPen(QColor(colour).darker(150)),
                    'data': tooltip,
                })
                self._tx_points.append((ts, yv, tooltip))

            if not spots:
                continue
            scat = pg.ScatterPlotItem(spots, pxMode=True, hoverable=True,
                                      hoverBrush=pg.mkBrush('y'),
                                      hoverPen=pg.mkPen('k', width=2))
            scat.setOpacity(0.6)
            self._plot.addItem(scat)
            self._scatters[sym] = scat

    # ------------------------------------------------------------------
    def _install_legend_toggles(self):
        legend = self._plot.legend
        if legend is None:
            return
        for sample, label in list(legend.items):
            name = label.text
            if name not in self._curves:
                continue
            def _toggle(_ev, _name=name):
                self._set_visible(_name, not self._curve_visible.get(_name, True))
            sample.mouseClickEvent = _toggle
            label.mouseClickEvent = _toggle

    def _set_visible(self, name: str, vis: bool):
        curve = self._curves.get(name)
        if curve is None:
            return
        curve.setVisible(vis)
        self._curve_visible[name] = vis
        sc = self._scatters.get(name)
        if sc is not None:
            sc.setVisible(vis)
        legend = self._plot.legend
        if legend is not None:
            for sample, label in legend.items:
                if label.text == name:
                    label.setOpacity(1.0 if vis else 0.35)
                    sample.setOpacity(1.0 if vis else 0.35)
        if vis:
            self.cur_shown_stock.add(name)
        else:
            self.cur_shown_stock.discard(name)

    def _apply_shown_stock(self, starthidden: bool, isline: bool):
        if not isline:
            return
        shown = set(self.params.shown_stock or [])
        if shown:
            for name in list(self._curves.keys()):
                self._set_visible(name, name in shown)
            self.cur_shown_stock = set(shown)
        elif starthidden:
            for name in list(self._curves.keys()):
                self._set_visible(name, False)
            self.cur_shown_stock = set()
        else:
            self.cur_shown_stock = set(self._curves.keys())

    # ------------------------------------------------------------------
    # Native mplcursors-style hover.
    def _install_hover(self):
        plot = self._plot
        if self._vline is None:
            self._vline = pg.InfiniteLine(angle=90, movable=False,
                                          pen=pg.mkPen('r', style=Qt.DashLine))
            self._vline.setZValue(50)
            self._vline.hide()
            plot.addItem(self._vline, ignoreBounds=True)
        if self._tooltip is None:
            self._tooltip = pg.TextItem(anchor=(0, 1), color='k',
                                        fill=pg.mkBrush(255, 255, 220, 220),
                                        border=pg.mkPen(120, 120, 120))
            self._tooltip.setZValue(60)
            self._tooltip.hide()
            plot.addItem(self._tooltip, ignoreBounds=True)

        if self._hover_proxy is not None:
            try:
                self._hover_proxy.disconnect()
            except Exception:
                pass
        self._hover_proxy = pg.SignalProxy(plot.scene().sigMouseMoved,
                                           rateLimit=60,
                                           slot=self._on_mouse_moved)

    @simple_exception_handling(err_description="hover annotation failed",
                                never_throw=True)
    def _on_mouse_moved(self, evt):
        pos = evt[0]
        plot = self._plot
        if not plot.sceneBoundingRect().contains(pos):
            self._vline.hide()
            self._tooltip.hide()
            self._set_highlight(None)
            return
        mouse_pt: QPointF = plot.vb.mapSceneToView(pos)
        x = float(mouse_pt.x())
        y = float(mouse_pt.y())

        rows, target = self._build_annotation_rows(x, y)
        if not rows:
            self._vline.hide()
            self._tooltip.hide()
            self._set_highlight(None)
            return

        html_parts = []
        for name, body in rows:
            if name is None:
                html_parts.append(body)
                continue
            if name == target:
                html_parts.append(f'<b>{name}: {body}</b>')
            else:
                html_parts.append(f'{name}: {body}')
        import datetime as _dt
        try:
            html_parts.append(_dt.datetime.utcfromtimestamp(x)
                              .strftime('%Y-%m-%d'))
        except (ValueError, OSError):
            pass
        self._tooltip.setHtml('<br>'.join(html_parts))
        self._tooltip.setPos(x, y)
        self._tooltip.show()
        self._vline.setPos(x)
        self._vline.show()
        self._set_highlight(target)

    def _build_annotation_rows(self, x: float, y: float):
        """Return (rows, target_name).

        rows: list of (name|None, body_html). name=None means a separator
              or transaction tooltip (rendered verbatim).
        target_name: name of the curve closest to the cursor's y (the one
              to bold), or None.
        """
        is_pct = bool(self.typ is not None and (self.typ & (Types.PRECENTAGE | Types.DIFF)))
        rows: list[tuple[Optional[str], str]] = []
        target = None
        best_dy = math.inf
        for name, curve in self._curves.items():
            if not self._curve_visible.get(name, True):
                continue
            xd, yd = curve.getData()
            if xd is None or len(xd) == 0 or x < xd[0] or x > xd[-1]:
                continue
            yv = float(np.interp(x, xd, yd))
            if math.isnan(yv):
                continue
            orig_val = self._interp_orig(name, x) if is_pct else None
            suffix = '%' if is_pct else ''
            extra = f' ({_round2(orig_val)})' if orig_val is not None else ''
            body = f'{round(yv, 2)}{suffix}{extra}'
            rows.append((name, body))
            dy = abs(yv - y)
            if dy < best_dy:
                best_dy = dy
                target = name

        hit = self._nearest_tx(x)
        if hit is not None:
            rows.append((None, '---'))
            rows.append((None, hit.replace('\n', '<br>')))
        return rows, target

    def _set_highlight(self, name: Optional[str]):
        """Thicken the bolded curve so the selection reads on the plot
        itself, not just in the tooltip. Idempotent; cheap (only touches
        pens when the target changes)."""
        if getattr(self, '_highlighted', None) == name:
            return
        prev = getattr(self, '_highlighted', None)
        if prev and prev in self._curves:
            pen = self._curves[prev].opts.get('pen')
            if pen is not None:
                try:
                    pen.setWidth(2)
                    self._curves[prev].setPen(pen)
                except Exception:
                    pass
        if name and name in self._curves:
            pen = self._curves[name].opts.get('pen')
            if pen is not None:
                try:
                    pen.setWidth(4)
                    self._curves[name].setPen(pen)
                except Exception:
                    pass
        self._highlighted = name

    def _nearest_tx(self, x: float):
        """Return tooltip text for the transaction nearest to view-x, if
        within a small pixel radius; else None. Pixel-based so it adapts
        to zoom level."""
        if not self._tx_points or self._plot is None:
            return None
        vb = self._plot.vb
        xr = vb.viewRange()
        xspan = max(1e-9, xr[0][1] - xr[0][0])
        # ~6 pixels in view coords, given current viewport width.
        vw = max(1.0, vb.width())
        tol = (6.0 / vw) * xspan
        best = None
        best_d = tol
        for tx, _ty, txt in self._tx_points:
            d = abs(tx - x)
            if d < best_d:
                best_d = d
                best = txt
        return best

    def _interp_orig(self, name: str, x: float):
        if self.orig_data is None or name not in self.orig_data.columns:
            return None
        try:
            yv = self.orig_data[name].to_numpy(dtype='float64')
        except Exception:
            return None
        if self._orig_epoch is None or len(self._orig_epoch) == 0:
            return None
        if x < self._orig_epoch[0] or x > self._orig_epoch[-1]:
            return None
        val = float(np.interp(x, self._orig_epoch, yv))
        return None if math.isnan(val) else val
