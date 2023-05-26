import logging
import logging
import math
import time
from contextlib import suppress
from datetime import timedelta
from functools import partial

import matplotlib

from common.loghandler import TRACELEVEL
from engine.compareengineinterface import CompareEngineInterface
from gui.formobserverinterface import ResetRanges

matplotlib.set_loglevel("INFO")
import mplcursors
from PySide6.QtCore import QMutex, QRecursiveMutex
# from matplotlib import pyplot as plt
import numpy
from config import config

USEQT = config.UI.USEQT
from common.common import Types, simple_exception_handling


# plt.rcParams["figure.autolayout"] = False


@simple_exception_handling(err_description="simple err",never_throw=True)
def show_annotation(sel, cls=None, ax=None, generation=None):
    cls.generation_mutex.lock()
    logging.log(TRACELEVEL, ('show locked'))
    try:

        if cls.generation != generation:
            logging.log(TRACELEVEL, ('ignoring diff generation'))
            with suppress(ValueError):
                sel.annotation.remove()
            for artist in sel.extras:
                with suppress(ValueError):
                    artist.remove()

            return

        xi = sel.target[0]
        vertical_line = ax.axvline(xi, color='red', ls=':', lw=1)
        sel.extras.append(vertical_line)
        date = matplotlib.dates.num2date(xi)
        names = [k._label for k in ax.legend_.legendHandles]
        if cls.typ & (Types.PRECENTAGE | Types.DIFF):
            ls = list(map(matplotlib.dates.date2num, cls.orig_data.index.to_list()))
            vals_orig=[numpy.interp(xi, ls, cls.orig_data[n]) for n in names]
        else:
            vals_orig = [None] * len(names)

        get_val = lambda n: f"({round(n, 2)})" if n is not None else ''
        val = [(round(numpy.interp(xi, ll._x, ll._y), 2), ll._visible, ll == sel[0]) for ll in ax.lines]

        stls = [(f'{n}: {v1}{"%" if cls.typ & Types.PRECENTAGE else ""} {get_val(val_orig)}', targ)
                for n, (v1, vis, targ),val_orig in
                zip(names, val,vals_orig) if vis and not math.isnan(v1)]

        annotation_str = '\n'.join(
         [(s if not targ else ((r' $\bf{ %s }$' % s).replace('%', '\\%'))) for s,targ in stls ])


        annotation_str += '\n' + str(date.strftime('%Y-%m-%d'))

        sel.annotation.set_text(annotation_str)
        cls.anotation_list += [sel]

    finally:
        logging.log(TRACELEVEL, ('show unlock'))
        cls.generation_mutex.unlock()
    # cls._annotation+=ann


class GraphGenerator:
    B = (1, 0.5)

    def get_visible_cols(self):
        ax=self._axes
        vis=[l.get_visible() for l in ax.lines]
        names = [k._label for k in ax.legend_.legendHandles]
        l=filter(lambda x: x[1] ,zip(names, vis))
        return list(map(lambda x:x[0],l))

    @property
    def params(self):
        return self._eng.params

    def __init__(self, eng, axes):
        self._eng: CompareEngineInterface = eng
        self._axes = axes
        self._linesandfig = []
        self.last_stock_list = set()
        self.cur_shown_stock = set()
        self.first_time = True
        self.generation_mutex = QRecursiveMutex()
        self.generation = 0
        self.anotation_list = []

    def get_title(self):
        type = self.params.type

        def rel(type):
            dic = {}
            dic[Types.RELTOMAX] = 'relative to maximum '
            dic[Types.RELTOMIN] = 'relative to minimum '
            dic[Types.RELTOEND] = 'relative to end '
            dic[Types.RELTOSTART] = '' if type & Types.COMPARE else 'relative to start time '
            return dic.get(type & (Types.RELTOSTART | Types.RELTOMAX | Types.RELTOMIN | Types.RELTOEND), '')

        def getbasetype(type):
            dic = {}
            dic[Types.PROFIT] = 'Unrealized profit'
            dic[Types.VALUE] = 'Value'
            dic[Types.PRICE] = 'Stock price'
            dic[Types.TOTPROFIT] = 'Total profit'
            dic[Types.PERATIO] = 'PE Ratio'
            dic[Types.PRICESELLS] = 'Price to sells'
            dic[Types.THEORTICAL_PROFIT] = 'Theortical profit'
            dic[Types.RELPROFIT] = 'Realized Profit'
            return dic.get(type & (
                    Types.PROFIT | Types.VALUE | Types.PRICE | Types.RELPROFIT | Types.TOTPROFIT | Types.PERATIO | Types.PRICESELLS | Types.THEORTICAL_PROFIT),
                           dic[Types.PRICE])

        lowerfirst = lambda x: x[0].lower() + x[1:]
        dic = {}
        dic[Types.PRECENTAGE] = lambda s: f'Percentage change {rel(type)}of {lowerfirst(s)}'
        dic[Types.PRECDIFF] = lambda s: f'Percentage change difference {rel(type)}of {lowerfirst(s)}'
        dic[Types.DIFF] = lambda s: f'Difference {rel(type)}of {lowerfirst(s)}'
        dic[Types.ABS] = lambda s: s
        if ((type & Types.COMPARE) == 0) and type & (Types.PRECENTAGE | Types.DIFF):
            type = type & ~Types.DIFF  # percentage diff when not comparing is meaningless
        basestr = dic.get(type & (Types.PRECENTAGE | Types.PRECDIFF | Types.DIFF), dic[Types.ABS])

        st = basestr(getbasetype(type))
        if type & Types.COMPARE and self.params.compare_with:
            st += ' compared with ' + self.params.compare_with
        return st

    def gen_actual_graph(self, cols, dt, isline, starthidden, just_upd, type, orig_data,adjust_date=False):
        additional_options = config.UI.ADDITIONALOPTIONS
        self.generation_mutex.lock()
        logging.log(TRACELEVEL, ('generation locked'))

        self.orig_data = orig_data
        self.typ = type

        # plt.sca(self._axes)
        try:
            if not just_upd:
                self.cur_shown_stock = set()
                logging.log(TRACELEVEL, ('not  justupdate'))
                self.remove_all_anotations()
            if just_upd:
                logging.log(TRACELEVEL, ('calledreomve!'))

                self.remove_all_anotations()
                ar = self._axes
                dt.plot.line(reuse_plot=True, ax=ar, grid=True, **additional_options)


            else:

                if not isline:
                    ar = dt.plot.area(stacked=False)
                else:
                    # mplfinance.plot(dt, figsize=(16, 10), type='candle')
                    ar = self._axes
                    dt.plot.line(reuse_plot=True, ax=ar, grid=True, **additional_options)
                    if USEQT:
                        self.cid = ar.figure.canvas.mpl_connect('pick_event', partial(GraphGenerator.onpick, self))
            if ar is None:
                return
            FACy = 1.2
            FACx = 2.4
            box = ar.get_position()
            ar.set_position([0, box.y0, 6 * FACx, box.height])
            mfig = ar.figure

            ar.set_title(self.get_title())

            # Put a legend to the right of the current aris
            if len(cols) >= config.UI.MINCOLFORCOLUMS:

                ar.legend(loc='center left', bbox_to_anchor=self.B, ncol=len(cols) // config.UI.MINCOLFORCOLUMS,
                          handleheight=2.4, labelspacing=0.05)
            else:
                ar.legend(loc='center left', bbox_to_anchor=self.B, handleheight=2.4, labelspacing=0.05)
            if isline:
                self.handle_line(ar, starthidden, just_upd)

            mfig.autofmt_xdate()

            ax = ar
            ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%Y-%m-%d'))

            self.cursor = mplcursors.cursor(mfig, hover=True)
            self.generation += 1
            self.cb = self.cursor.connect('add', partial(show_annotation, cls=self, ax=ar, generation=self.generation))

            if just_upd:

                self.update_limit(ar, ar.legend_.figure, mfig, ar.lines)
                if adjust_date or self.first_time:
                    self.first_time = False
                    mind = matplotlib.dates.date2num(min(dt.index))
                    maxd = matplotlib.dates.date2num(max(dt.index))
                    if mind < maxd:
                        self._axes.set_xlim([mind, maxd])

                    # plt.draw()
            elif self.params.show_graph:
                logging.debug(('strange'))
                pass  # plt.show()
            # self.remove_all_anotations()
        finally:
            logging.log(TRACELEVEL, ('generation unlocked'))
            self.generation_mutex.unlock()

    def remove_all_anotations(self):
        if self._axes is None:
            return
        if getattr(self, 'cursor', None):
            self.cursor.remove()

            # time.sleep(0.2)
            self.cursor.disconnect('add', cb=self.cb)
            # self.cb=lambda :None
            logging.log(TRACELEVEL, (self.cursor._callbacks))
            self.cursor._callbacks['add'] = {}

        for child in self._axes.get_children():
            if isinstance(child, matplotlib.lines.Line2D):
                child.remove()

        if getattr(self, 'cursor', None):
            self._axes.figure.canvas.callbacks.disconnect(self.cb)
            del self.cursor

    def handle_line(self, ar, starthidden, just_upd):
        lined = dict()
        leg = ar.legend_
        fig = leg.figure
        nlst = set([x._label for x in leg.get_lines()])
        if self.last_stock_list != nlst:
            if self.last_stock_list < nlst or (self.cur_shown_stock != self.cur_shown_stock.intersection(
                    nlst)):  # if there are more stocks , or we removed a stock that was shown
                self.cur_shown_stock = set()

        istrivial = (len(self.params.shown_stock) == 0 or len(self.params.shown_stock) == len(ar.lines))
        iscurtrivial = (len(self.cur_shown_stock) == 0 or len(self.cur_shown_stock) == len(ar.lines))
        if (iscurtrivial and starthidden):
            self.cur_shown_stock = set()
        if not istrivial:
            self.cur_shown_stock = self.params.shown_stock

        for origline, legline in zip(ar.lines, leg.get_lines()):
            legline.set_picker(5)  # 5 pts tolerance

            if not istrivial:
                hide = legline._label not in self.params.shown_stock  # act based on shown_stock
            else:
                hide = (iscurtrivial and starthidden) or (
                        not iscurtrivial and (legline._label not in self.cur_shown_stock))

            if hide:
                legline.set_alpha(0.2)  # hide
                origline.set_visible(0)
            else:
                self.cur_shown_stock.add(legline._label)  # maybe there
                legline.set_alpha(1)  # hide
                origline.set_visible(1)
        self.last_stock_list = nlst
        return (lined, fig)

    def update_limit(self, ar, fig, ofig, lines):

        MAXV = 100000000000
        maxline = -1 * MAXV
        minline = MAXV
        for l in lines:
            if l.get_visible():
                y = list(filter(lambda x: not math.isnan(x), l._y))
                if len(y) == 0:
                    continue
                # x = list(filter(lambda x:not math.isnan(x) , l._x))
                maxline = max(maxline, max(y))
                minline = min(minline, min(y))
            # self.maxValue=0 if maxline==(-1)* MAX  V else maxline
            # self.minValue=0 if minline== MAXV else minline
        if maxline == minline:
            ar.set_ylim(ymin=minline - 0.12 * minline, ymax=maxline + 0.12 * maxline)
        else:
            try:
                ar.set_ylim(ymin=minline - 0.12 * abs(max(minline, maxline - minline)),
                            ymax=maxline + 0.12 * abs(max(maxline, maxline - minline)))
            except ValueError:
                logging.debug(('val error'))

        # fig.canvas.draw()
        # ofig.canvas.draw()
        # ofig.canvas.flush_events()

    def onpick(self, event):
        # on the pick event, find the orig line corresponding to the
        # legend proxy line, and toggle the visibility
        # legline = event.artist
        b = False
        ar = self._axes
        fig = ar.legend_.figure
        for origline, legline in zip(ar.lines, ar.legend_.get_lines()):
            if legline == event.artist:
                # origline = lined[legline]
                vis = not origline.get_visible()
                origline.set_visible(vis)

                # Change the alpha on the line in the legend so we can see what lines
                # have been toggled
                if vis:
                    legline.set_alpha(1.0)
                    self.cur_shown_stock.add(legline._label)
                else:
                    legline.set_alpha(0.2)
                    self.cur_shown_stock.remove(legline._label)
                b = True
                break
        if b:
            self.update_limit(ar, fig, origline.figure, ar.lines)
            if USEQT:
                fig.canvas.draw()  # draw
        else:
            logging.log(TRACELEVEL, ("onpick failed"))
        # self._ax=

    def show_hide(self, toshow):
        ar = self._axes
        leg = ar.legend_
        fig = leg.figure
        for origline, legline in zip(ar.lines, leg.get_lines()):
            if not toshow:
                legline.set_alpha(0.2)
                origline.set_visible(0)
            else:
                legline.set_alpha(1)
                origline.set_visible(1)
        if USEQT:
            fig.canvas.draw()  # draw
