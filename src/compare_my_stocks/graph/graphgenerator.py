import dataclasses
import datetime
import logging
import logging
import math
import threading
import time
from collections import defaultdict, namedtuple
from contextlib import suppress
from datetime import timedelta
from functools import partial, lru_cache
import random

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib
import numpy as np
from matplotlib.axes import Axes
from matplotlib.collections import PathCollection
from matplotlib.legend_handler import HandlerPathCollection

try:

    from common.dolongprocess import DoLongProcessSlots, TaskParams
except:
    pass #testing

from common.loghandler import TRACELEVEL
from engine.compareengineinterface import CompareEngineInterface

matplotlib.set_loglevel("INFO")
import mplcursors
from PySide6.QtCore import QMutex, QRecursiveMutex
# from matplotlib import pyplot as plt
import numpy
from config import config

UseQT = config.UI.UseQT
from common.common import Types, lmap, selfifnn, ifnn, timeit, UniteType
from common.simpleexceptioncontext import simple_exception_handling

# plt.rcParams["figure.autolayout"] = False
get_val = lambda n: f"({round(n, 2)})" if n is not None else ''
round_til_2 = lambda n: f"{round(n, 2)}" if n is not None else ''

def mscatter(x,y,ax=None, m=None, **kw):
    import matplotlib.markers as mmarkers
    if not ax: ax=plt.gca()
    sc = ax.scatter(x,y,**kw)
    if (m is not None) and (len(m)==len(x)):
        paths = []
        for marker in m:
            if isinstance(marker, mmarkers.MarkerStyle):
                marker_obj = marker
            else:
                marker_obj = mmarkers.MarkerStyle(marker)
            path = marker_obj.get_path().transformed(
                        marker_obj.get_transform())
            paths.append(path)
        sc.set_paths(paths)

    return sc

@simple_exception_handling(err_description="simple err", never_throw=True)
def show_annotation(sel, cls, ax, generation):
    cls.generation_mutex.lock()
    logging.log(TRACELEVEL, ('show locked'))
    try:

        if cls.generation != generation:
            logging.debug(('ignoring diff generation'))
            with suppress(ValueError):
                sel.annotation.remove()
            for artist in sel.extras:
                with suppress(ValueError):
                    artist.remove()

            return
        if type(sel.artist) == matplotlib.collections.PathCollection:
            generic=False

            annotation_str = cls.point_to_annotation.get(tuple(sel.target))
            if annotation_str is None:
                generic=True

        else:
            generic = True

        if generic:
            xi = sel.target[0]
            vertical_line = ax.axvline(xi, color='red', ls=':', lw=1)
            sel.extras.append(vertical_line)
            date = matplotlib.dates.num2date(xi)
            names = [k._label for k in ax.legend_.legendHandles]
            if cls.typ & (Types.PRECENTAGE | Types.DIFF):
                ls = list(map(matplotlib.dates.date2num, cls.orig_data.index.to_list()))
                vals_orig = [numpy.interp(xi, ls, cls.orig_data[n]) for n in names]

                
            else:
                vals_orig = [None] * len(names)
                

            val = [(round(numpy.interp(xi, ll._x, ll._y), 2), ll._visible, ll == sel[0]) for ll in ax.lines]
            basic_str= lambda n,v1,val_orig   :     (f'{n}: {v1}{"%" if cls.typ & Types.PRECENTAGE else ""} {get_val(val_orig)}')
            hold_str = lambda hold,price: f'(qty: {round_til_2(hold)} price: {round_til_2(price)})'

            if cls.additional_df and ( ( cls.typ & (Types.RELPROFIT | Types.PROFIT | Types.VALUE | Types.TOTPROFIT) )
            ) and (cls.unitetype & (UniteType.ADDTOTALS) == UniteType.NONE) :
                ls = list(map(matplotlib.dates.date2num, cls.orig_data.index.to_list()))
                holding_orig = [numpy.interp(xi, ls, cls.additional_df[0][n]) for n in names]
                price_orig = [numpy.interp(xi, ls, cls.additional_df[1][n]) for n in names]
                stls = [ ( basic_str(n,v1,val_orig) , hold_str(hold,price) ,targ)
                        for n, (v1, vis, targ), val_orig,hold,price in
                        zip(names, val, vals_orig, holding_orig,price_orig) if vis and not math.isnan(v1)]
            else:                 
                stls = [ (basic_str(n,v1,val_orig) ,'',targ)
                        for n, (v1, vis, targ), val_orig in
                        zip(names, val, vals_orig) if vis and not math.isnan(v1)]

            annotation_str = '\n'.join(
                [(s if not targ else ((r' $\bf{ %s }$' % s).replace('%', '\\%')+ ( '\n'+additional if additional else '') )) for s,additional, targ in stls])

            annotation_str += '\n' + str(date.strftime('%Y-%m-%d'))
        sel.annotation.set_horizontalalignment('left')
        sel.annotation.set_multialignment('left')
        sel.annotation.set_text(annotation_str)

        cls.anotation_list += [sel]

    finally:
        logging.log(TRACELEVEL, ('show unlock'))
        cls.generation_mutex.unlock()
    # cls._annotation+=ann
StringPointer=namedtuple('StringPointer', ['originalLocation', 'string'])
class GraphGenerator:
    B = (1, 0.5)

    def get_visible_cols(self):
        ax = self._axes
        vis = [l.get_visible() for l in ax.lines]
        names = [k._label for k in ax.legend_.legendHandles]
        l = filter(lambda x: x[1], zip(names, vis))
        return list(map(lambda x: x[0], l))

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
        self.point_to_annotation = {}
        self.lines_dict= {}
        self.symbols_to_blobs = defaultdict(list)
        self.pick_lock= threading.Lock()
        self.last_pick_event = None

        if eng is not None: #for testing
            self._unit_blob_task= DoLongProcessSlots(self.unite_blobs)

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

    def extract_data(self,plot_data,special=False):
        @lru_cache(maxsize=1)
        def getfigheigt():
            t = self.ax.transAxes.transform([(0, 0), (1, 1)])
            t = self.ax.get_figure().get_dpi() / (t[1, 1] - t[0, 1]) / 72
            _, fig_height = self.ax.figure.get_size_inches()
            return fig_height
        #allcolors = gencolors(len(plot_data))
        total = np.array([])
        fig_height=getfigheigt()
        for symbol, symbol_data in plot_data.items():
            mpl_dates, cost, qtys, sources, adjustedpr = zip(*symbol_data)
            total= np.append(total, np.abs(np.array(qtys) * np.array(cost)))

            typical = np.average(total)
            if max(total) > 5 * typical:
                typical = max(total) / 2

        for symbol, symbol_data in plot_data.items():
            mpl_dates, cost, qtys, sources, adjustedpr = zip(*symbol_data)
            if len(cost) == 0:
                continue

            if special:
                ll=self.lines_dict.get(symbol)
                if ll is None:
                    logging.error('no line for %s', symbol)
                    continue
                xs = np.array(lmap(matplotlib.dates.date2num,mpl_dates),dtype='float64')
                yval=numpy.interp(xs, ll._x, ll._y)
            else:
                yval = [selfifnn(d, c) for c, d in zip(cost, adjustedpr)]


            total = np.abs(np.array(qtys) * np.array(cost))

            # Create a scatter plot

            sizes = ((np.array(total) / typical) * (fig_height * 72)  * config.UI.CircleSizePercentage)**2  # 5% of y-range
            #sizes= np.fmax(sizes,np.array([typical/3 * (fig_height * 72)  * config.UI.CircleSizePercentage ] * len(sizes)))

            #
            # r = next(allcolors)
            # red = [1, 0.1, 0.1]
            # reddier = np.convolve(*lmap(np.array, [red, r]), mode='same')
            # if np.max(reddier) > 1:
            #     reddier = reddier / np.max(reddier)
            #colors = [(reddier if (q < 0) else r) for q in qtys]
            m= ['s' if (q < 0) else 'o' for q in qtys]
            #see https://stackoverflow.com/questions/14827650/pyplot-scatter-plot-marker-size
            #want to make same trasactions same size.
            sizes = [(s*3.14/4)  if (q < 0) else s for q,s in zip(qtys,sizes)]
            yield m,sizes, mpl_dates, yval, symbol,cost, adjustedpr, qtys, sources
    @timeit
    def plot_transaction_info(self, ax, plot_data,special=False):

        # def gencolors(num):
        #     phi = np.linspace(0, 2 * np.pi, 60)
        #     rgb_cycle = (np.stack((np.cos(phi),  # Three sinusoids,
        #                            np.cos(phi + 2 * np.pi / 3),  # 120° phase shifted,
        #                            np.cos(phi - 2 * np.pi / 3)
        #                            )).T  # Shape = (60,3)
        #                  + 1) * 0.5
        #     for k in range(0,len(rgb_cycle), len(rgb_cycle)//num):
        #         yield rgb_cycle[k]

        # def random_color():
        #     red = [1, 0, 0]
        #     white = [1, 1, 1]
        #     while True:
        #         color = [random.random(), random.random(), random.random()]  # Generate a random color
        #         color = lmap(lambda x: x * 0.8 + 0.1, color)
        #         if sum([(a - b) ** 2 for a, b in
        #                 zip(color, white)]) < 0.2:
        #             continue  # Check if the color is close to white
        #
        #         if sum([(a - b) ** 2 for a, b in
        #                 zip(color, red)]) > 0.2:  # Check if the color is different enough from red
        #             return color



        allxy= list()

        try:
            self._unit_blob_task.mutex.lock()

            self.tmp_point_to_annotation = defaultdict(set)

            for m,sizes, mpl_dates, yval, symbol,cost, adjustedpr, qtys, sources in self.extract_data(plot_data,special=special):
                mscatter(mpl_dates, yval, s=sizes, m=m , alpha=0.5,label=symbol,ax=ax)


                for i, (t, y, a, q, s,curyval,ss) in enumerate(zip(mpl_dates, cost, adjustedpr, qtys, sources,yval,sizes)):
                    str_with_adj = lambda x, adj: f" {round_til_2(x)} (adj. {round_til_2(adj)} )" if adj else round_til_2(x)
                    curloc = (matplotlib.dates.date2num(t), curyval)
                    while curloc in self.tmp_point_to_annotation:
                        logging.debug("duplicate point %s %s", t, curyval)
                        curloc=(curloc[0]+ 0.0001, curloc[1])
                    allxy.append( ( curloc ,ss ))



                    st= StringPointer(string='%s Date: %s \nCost: %s\nQty: %s\n Source %s\n' % (
                        r' $\bf{ %s }$' % symbol,
                        t.strftime(
                            '%d/%m/%Y %H:%M'),
                        str_with_adj(y, a),
                        str_with_adj(q, ifnn(a, lambda: q * (y / a))),
                        s),originalLocation=curloc)

                    self.tmp_point_to_annotation[curloc].add(st)

        finally:
            self._unit_blob_task.mutex.unlock()




        self._unit_blob_task.command.emit(TaskParams(params=(allxy,)))


    def unite_blobs(self,allxy):
        allxy.sort(key=lambda x: x[1])

        # Check for overlap and adjust
        for i in range(0, len(allxy)):
            for j in range(i + 1, len(allxy)):
                source , s = allxy[i]
                destination, d = allxy[j]
                distance = self.diff_func( source[0],destination[0], source[1], destination[1])

                if (math.sqrt(s) / 2 + math.sqrt(d) / 2) > distance / 72:

                    if len(self.tmp_point_to_annotation[destination]) == 0 and len(self.tmp_point_to_annotation[source]) != 0 :
                        logging.debug(("really strange",i,j))
                        self.tmp_point_to_annotation[destination].update(self.tmp_point_to_annotation[source])

                    elif len(self.tmp_point_to_annotation[source])!=0:
                        self.tmp_point_to_annotation[destination].update(self.tmp_point_to_annotation[source])
                        self.tmp_point_to_annotation[source] = set()
                        logging.debug( (f"{source} to {destination}",i,j))
                        break
        self.point_to_annotation={}
        for k, ls in self.tmp_point_to_annotation.items():
            newstring='\n'.join([it.string for it in ls ])
            for it in ls:
                self.point_to_annotation[it.originalLocation]=newstring #let all transfered locations point to the same string
            self.point_to_annotation[k]=newstring


        self.tmp_point_to_annotation= defaultdict(set)

    def diff_func(self, xa, xb, ya, yb):
        diffy = abs(ya - yb)
        diffx = abs(xa - xb)
        origin = self.ax.figure.dpi_scale_trans.transform((0, 0))
        vec = self.ax.figure.dpi_scale_trans.transform((diffx, diffy))
        vec = np.array(vec) - np.array(origin)
        distance = np.linalg.norm(vec, ord=2)  # distange on display node
        return distance

    def order_labels(self,ar : Axes):
        handles, labels = ar.get_legend_handles_labels()
        lines = []
        line_labels = []
        collections = []
        collection_labels = []

        # separate handles into Line2D and PathCollection
        for h, l in zip(handles, labels):
            if isinstance(h, matplotlib.lines.Line2D):
                lines.append(h)
                line_labels.append(l)
            elif isinstance(h, matplotlib.collections.PathCollection):
                #h.set_sizes([config.UI.CircleSize])
                collections.append(h)
                collection_labels.append(l)

        # clear handles and labels
        handles = []
        labels = []

        # match Line2D and PathCollection with the same label
        for line_label in line_labels:
            line_index = line_labels.index(line_label)
            if line_label in collection_labels:
                collection_index = collection_labels.index(line_label)

                handles.append((lines[line_index],collections[collection_index]))
                labels.append(line_label)
                #handles.append()
                #labels.append("")  # empty label for collections
            else:
                handles.append(lines[line_index])
                labels.append(line_label)

        return handles, labels

    @simple_exception_handling("Error while generating graph",err_to_ignore=[TypeError],always_throw=True)
    def gen_actual_graph(self, cols, dt, isline, starthidden, just_upd, type, unitetype,orig_data, adjust_date=False,
                         plot_data=None,additional_df=None):
        def update_prop(handle, orig):
            marker_size = 36
            handle : PathCollection
            handle.update_from(orig)
            handle.set_sizes([marker_size])
            import matplotlib.markers as mmarkers
            marker_obj= mmarkers.MarkerStyle('o')
            path = marker_obj.get_path().transformed(
                marker_obj.get_transform())
            handle.set_paths([path])


        additional_options = config.UI.AdditionalOptions
        self.generation_mutex.lock()
        logging.log(TRACELEVEL, ('generation locked'))

        self.orig_data = orig_data
        self.additional_df = additional_df
        self.typ = type
        self.unitetype=unitetype 

        # plt.sca(self._axes)
        try:
            self.remove_all_anotations()
            self.point_to_annotation = {}
            if not just_upd:
                self.cur_shown_stock = set()
                logging.log(TRACELEVEL, ('not  justupdate'))


                # logging.debug (('calledreomve!'))
            ar = self._axes
            dt.plot.line(reuse_plot=True, ax=ar, grid=True, **additional_options)

            if just_upd or self.first_time:
                if UseQT:
                    self.cid = ar.figure.canvas.mpl_connect('pick_event', partial(GraphGenerator.onpick, self))

            if ar is None:
                return
            FACy = 1.2
            FACx = 2.4
            box = ar.get_position()
            ar.set_position([0, box.y0, 6 * FACx, box.height])
            mfig = ar.figure

            ar.set_title(self.get_title())



            mfig.autofmt_xdate()

            self.ax = ar
            self.ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%Y-%m-%d'))

            if just_upd:

                self.update_limit(ar, ar.legend_.figure, mfig, ar.lines)
                if adjust_date or self.first_time:
                    mind = matplotlib.dates.date2num(min(dt.index))
                    maxd = matplotlib.dates.date2num(max(dt.index))
                    if mind < maxd:
                        self._axes.set_xlim([mind, maxd])

                    plt.draw()
            elif self.params.show_graph:
                logging.debug('strange')
                pass  # plt.show()
            if plot_data and self.params.show_transactions_graph:
                #special if not a price graph
                self.plot_transaction_info(ar, plot_data, special=
                (self.params.adjust_to_currency or self.params.adjusted_for_base_cur)  or not
                ( (Types.PRICE & type) == Types.PRICE or type==Types.ABS))

            # self.remove_all_anotations()
            self.cursor = mplcursors.cursor(mfig, hover=True)
            self.generation += 1
            self.cb = self.cursor.connect('add', partial(show_annotation, cls=self, ax=ar, generation=self.generation))

            handles, labels = self.order_labels(ar)
            self.handles_labels = { l: h for h, l in zip(handles, labels)}
            # Put a legend to the right of the current aris
            if len(cols) >= config.UI.MinColForColumns:

                lgnd=ar.legend(handles, labels, loc='center left', bbox_to_anchor=self.B, ncol=len(cols) // config.UI.MinColForColumns,
                               handleheight=2.4, labelspacing=0.05, handler_map={matplotlib.collections.PathCollection : HandlerPathCollection(update_func=update_prop)})
            else:
                lgnd=ar.legend(handles,labels, loc='center left', bbox_to_anchor=self.B, handleheight=2.4, labelspacing=0.05 , handler_map={matplotlib.collections.PathCollection : HandlerPathCollection(update_func=update_prop)})
            self.blobs_legends = {l._label: l for l in ar.get_legend_handles_labels()[0] if
                             isinstance(l, matplotlib.collections.PathCollection)}

            self.lines_dict= { l._label : l for l in ar.get_children() if isinstance(l, matplotlib.lines.Line2D)}
            self.lgnd= lgnd



            if isline:
                self.handle_line(ar, starthidden, just_upd)



        finally:
            self.first_time = False
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
            if isinstance(child, matplotlib.collections.PathCollection):
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
                if legline._label in self.blobs_legends:
                    self.blobs_legends[legline._label].set_alpha(0.2)
            else:
                self.cur_shown_stock.add(legline._label)  # maybe there
                legline.set_alpha(1)  # hide
                origline.set_visible(1)
                if legline._label in self.blobs_legends:
                    self.blobs_legends[legline._label].set_alpha(0.5)
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

        with self.pick_lock:
            if self.last_pick_event is not None:
                if datetime.datetime.now() - self.last_pick_event < datetime.timedelta(seconds=0.5):
                    return
            # on the pick event, find the orig line corresponding to the
            # legend proxy line, and toggle the visibility
            # legline = event.artist
            b = False
            ar = self._axes
            fig = ar.legend_.figure
            blobs= { l._label : l for l in ar.get_children() if isinstance(l, matplotlib.collections.PathCollection)}

            for origline, legline in zip(ar.lines, ar.legend_.get_lines()):
                if legline == event.artist:
                    # origline = lined[legline]
                    vis = not origline.get_visible()
                     #to avoid double counting
                    origline.set_visible(vis)
                    self.last_pick_event= datetime.datetime.now()
                    logging.debug(('onpick legend hide or show', origline._label, vis))
                    time.sleep(0.1)
                    if legline._label in blobs:
                        blobs[legline._label].set_visible(vis)
                        #self.handles_labels[legline._label][1].set_visible(vis)
                        # if legline._label in self.blobs_legends:
                        #     self.blobs_legends[legline._label].set_alpha(0.2 if vis else 0.5)

                    # Change the alpha on the line in the legend so we can see what lines
                    # have been toggled
                    if vis:
                        legline.set_alpha(1.0)
                        self.cur_shown_stock.add(legline._label)
                    else:
                        legline.set_alpha(0.2)
                        self.cur_shown_stock.remove(legline._label)
                    break
            else:
                logging.log(TRACELEVEL, ("onpick failed"))
                return

            self.update_limit(ar, fig, origline.figure, ar.lines)
                # if UseQT:
                #    fig.canvas.draw()  # draw
        # self._ax=

    def show_hide(self, toshow):
        ar = self._axes
        leg = ar.legend_
        fig = leg.figure
        for l in ar.get_children():
            if isinstance(l, matplotlib.collections.PathCollection):
                l.set_visible(toshow)

        for origline, legline in zip(ar.lines, leg.get_lines()):
            if not toshow:
                legline.set_alpha(0.2)
                origline.set_visible(0)
            else:
                legline.set_alpha(1)
                origline.set_visible(1)
        if UseQT:
            fig.canvas.draw()  # draw
