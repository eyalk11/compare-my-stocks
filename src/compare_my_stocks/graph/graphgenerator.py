import math
import time
from contextlib import suppress
from functools import partial

import matplotlib
import mplcursors
from PySide6.QtCore import QMutex, QRecursiveMutex
#from matplotlib import pyplot as plt
import numpy
from config import config
USEQT=config.USEQT
from common.common import Types
#plt.rcParams["figure.autolayout"] = False


def show_annotation(sel,cls=None, ax=None,generation=None):

    cls.generation_mutex.lock()
    #print('show locked')
    try:

        if cls.generation!=generation:
            print('ignoring diff generation')
            with suppress(ValueError):
                sel.annotation.remove()
            for artist in sel.extras:
                with suppress(ValueError):
                    artist.remove()

            return

        xi = sel.target[0]
        vertical_line = ax.axvline(xi, color='red', ls=':', lw=1)
        sel.extras.append(vertical_line)

        val=[  ( round(numpy.interp(xi, ll._x, ll._y),2),ll._visible,ll==sel[0])  for ll in ax.lines ]
        names= [ k._label for k in ax.legend_.legendHandles  ]
        annotation_str = '\n'.join([    ('%s' if not targ else r' $\bf{ %s }$')  % (f'{n}: {v1}') for n,(v1,vis,targ) in zip(names,val) if vis and not math.isnan(v1)  ])
        annotation_str+='\n'+str(matplotlib.dates.num2date(xi).strftime('%Y-%m-%d'))

        sel.annotation.set_text(annotation_str)
        cls.anotation_list+=[sel]

    finally:
        #print('show unlock')
        cls.generation_mutex.unlock()
    #cls._annotation+=ann

class GraphGenerator:

    def __init__(self,axes):
        #self.params = None
        self._axes=axes
        self._linesandfig=[]
        self.last_stock_list=set()
        self.cur_shown_stock=set()
        self.adjust_date=False
        self.generation_mutex = QRecursiveMutex()
        self.generation=0
        self.anotation_list=[]

    def get_title(self):
        type=self.params.type

        def rel(type):
            dic={} 
            dic[Types.RELTOMAX] = 'Relative To Maximum '
            dic[Types.RELTOMIN] = 'Relative To Minimum '
            dic[Types.RELTOEND] = 'Relative To End '
            dic[Types.RELTOSTART] =   '' if type & Types.COMPARE else 'Relative To Start Time '
            return dic.get( type &   (Types.RELTOSTART | Types.RELTOMAX | Types.RELTOMIN | Types.RELTOEND) , '' )

        def getbasetype(type):    
            dic={} 
            dic[Types.PROFIT]     =     'Profit'
            dic[Types.VALUE]      =     'Value'
            dic[Types.PRICE]      =     'Stock Price'
            dic[Types.TOTPROFIT] = 'Total Profit'
            dic[Types.PERATIO]  =  'PE Ratio'
            dic[Types.PRICESELLS] = 'Price To Sells'
            dic[Types.THEORTICAL_PROFIT] = 'Theortical'
            return dic.get( type & ( Types.PROFIT | Types.VALUE | Types.PRICE | Types.TOTPROFIT | Types.PERATIO | Types.PRICESELLS | Types.THEORTICAL_PROFIT) ,dic[Types.PRICE])

        dic={}
        dic[Types.PRECENTAGE]  =     f'Percentage Change { rel(type)}Of %s'
        dic[Types.PRECDIFF] = f'Percentage Change Difference {rel(type)}Of %s'
        dic[Types.DIFF]       =     f'Difference {rel(type)}Of %s'
        dic[Types.ABS ] = '%s'
        basestr= dic.get( type &   ( Types.PRECENTAGE | Types.PRECDIFF | Types.DIFF) , dic[Types.ABS])
        st = basestr % getbasetype(type)  
        if type & Types.COMPARE and self.params.compare_with:
            st += ' Compared With ' + self.params.compare_with
        return st

    def gen_actual_graph(self, B, cols, dt, isline, starthidden, just_upd,type):
        additional_options=config.ADDITIONALOPTIONS
        self.generation_mutex.lock()
        print('generation locked')

        #plt.sca(self._axes)
        try:
            if not just_upd:
                self.cur_shown_stock = set()
                print('not  justupdate')
                self.remove_all_anotations()
            if just_upd:
                print('calledreomve!')
                #import ipdb
                #ipdb.set_trace()
                #plt.cla()
                #for ann in self._annotation:
                #    ann.remove()
                    #del ann
                self.remove_all_anotations()
                ar = self._axes
                dt.plot.line(reuse_plot=True, ax=ar,grid=True,**additional_options)
                #fig=
                #if just_upd:
                #    fig.canvas.mpl_disconnect(self.cid)



                #mplfinance.plot(dt,figsize=(16, 10), reuse_plot=True,ax=ar,type='candle')

                #ar.legend_.figure.canvas.clear()
                #ar.legend_.figure.canvas.draw()
            else:

                if not isline:
                    ar = dt.plot.area( stacked=False)
                else:
                    #mplfinance.plot(dt, figsize=(16, 10), type='candle')
                    ar = self._axes
                    dt.plot.line(reuse_plot=True, ax=ar,grid=True,**additional_options)
                    self.cid = ar.figure.canvas.mpl_connect('pick_event', partial(GraphGenerator.onpick, self))
            FACy = 1.2
            FACx = 2.4
            box = ar.get_position()
            ar.set_position([0, box.y0, 6*FACx, box.height])
            mfig = ar.figure

            ar.set_title(self.get_title() )

            # Put a legend to the right of the current aris
            if len(cols) >= config.MINCOLFORCOLUMS:

                ar.legend(loc='center left', bbox_to_anchor=B, ncol=len(cols) // config.MINCOLFORCOLUMS, handleheight=2.4, labelspacing=0.05)
            else:
                ar.legend(loc='center left', bbox_to_anchor=B,handleheight=2.4, labelspacing=0.05)
            if isline:
                self.handle_line(ar, starthidden,just_upd)
            #
            # if self.params.increase_fig or len(self._linesandfig)==0:
            #     # plt.figure(len(self.graphs))
            #
            #
            # else:


            mfig.autofmt_xdate()

            ax=ar
            ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%Y-%m-%d'))


            self.cursor = mplcursors.cursor(mfig, hover=True)
            self.generation += 1
            self.cb= self.cursor.connect('add', partial(show_annotation,cls=self,ax=ar,generation=self.generation))

            #plt.grid(visible=True)
            #self._ax=ax
            if just_upd:
                #with self._out:

                self.update_limit(ar, ar.legend_.figure, mfig, ar.lines)
                if self.adjust_date:
                    f,t = self._axes.get_xlim()
                    fromdateNum = matplotlib.dates.date2num(self.params.fromdate) if self.params.fromdate else f
                    todateNum = matplotlib.dates.date2num(self.params.todate) if self.params.todate else t
                    self._axes.set_xlim([fromdateNum,todateNum])
                    #plt.grid(b=True)
                    self.adjust_date=False
                    #plt.draw()
            elif self.params.show_graph:
                print('strange')
                pass#plt.show()
            #self.remove_all_anotations()
        finally:
            print('generation unlocked')
            self.generation_mutex.unlock()
                    #from IPython.core.display import display
                    #display(mfig)
                    #plt.gcf().set_size_inches(13.57,  5.8 )
                    #plt.show()
            #else:
            #    plt.draw()
                #plt.show(block=False)
            #print('aftershow')
        #time.sleep(2)

    def remove_all_anotations(self):
        # for x in self.anotation_list:
        #     try:
        #         x.remove()
        #     except:
        #         pass
        #if getattr(self, 'cursor', None):
            #self.cursor.remove()
            #self.cursor.disconnect('add', cb=self.cb)
        # for x in self.anotation_list:
        #     try:
        #         self.cursor.remove_selection(x)
        #         print('removed sel')
        #     except:
        #         pass
        if getattr(self, 'cursor', None):
            self.cursor.remove()

            #time.sleep(0.2)
            self.cursor.disconnect('add', cb=self.cb)
            #self.cb=lambda :None
            print(self.cursor._callbacks)
            self.cursor._callbacks['add'] = {}

        for child in self._axes.get_children():
            if isinstance(child, matplotlib.lines.Line2D):
                child.remove()

                # if isinstance(child, matplotlib.text.Annotation):
                #
                #     try:
                #         child.remove()
                #     except:
                #         print('zzs')
                #         pass


        if getattr(self, 'cursor', None):
            # self.cursor.remove()
            #self.cursor.disconnect('add', cb=self.cb)
            #self.cb
            self._axes.figure.canvas.callbacks.disconnect(self.cb)
            del self.cursor



    def handle_line(self,ar,starthidden,just_upd):
        lined=dict()
        leg = ar.legend_
        fig = leg.figure
        nlst = set([x._label for x in leg.get_lines()])
        if self.last_stock_list!=nlst:
            if self.last_stock_list<nlst or (self.cur_shown_stock!=self.cur_shown_stock.intersection(nlst)): #if there are more stocks , or we removed a stock that was shown
                self.cur_shown_stock=set()



        istrivial=( len(self.params.shown_stock)==0 or len(self.params.shown_stock)==len(ar.lines))
        iscurtrivial = (len(self.cur_shown_stock) == 0 or len(self.cur_shown_stock) == len(ar.lines))
        if (iscurtrivial and starthidden):
            self.cur_shown_stock=set()
        if not istrivial:
            self.cur_shown_stock=self.params.shown_stock


        for origline, legline in zip(ar.lines, leg.get_lines()):
            legline.set_picker(5)  # 5 pts tolerance

            if not istrivial:
                hide=   legline._label not in self.params.shown_stock #act based on shown_stock
            else:
                hide=  (iscurtrivial and starthidden) or (not iscurtrivial and   (legline._label not in self.cur_shown_stock))

            if hide:
                legline.set_alpha(0.2)  # hide
                origline.set_visible(0)
            else:
                self.cur_shown_stock.add(legline._label) #maybe there
                legline.set_alpha(1)  # hide
                origline.set_visible(1)
        self.last_stock_list = nlst
        return (lined, fig)

    def update_limit(self,ar,fig,ofig,lines):

        MAXV=100000000000
        maxline = -1 * MAXV
        minline = MAXV
        for l in lines:
            if l.get_visible():
                y = list(filter(lambda x: not math.isnan(x), l._y))
                if len(y)==0:
                    continue
                # x = list(filter(lambda x:not math.isnan(x) , l._x))
                maxline = max(maxline, max(y))
                minline = min(minline, min(y))
            #self.maxValue=0 if maxline==(-1)* MAX  V else maxline
            #self.minValue=0 if minline== MAXV else minline
        if maxline== minline:
            ar.set_ylim(ymin=minline - 0.12*minline,ymax=maxline+0.12*maxline)
        else:
            try:
                ar.set_ylim(ymin=minline-0.12*abs(max(minline,maxline-minline)), ymax=maxline+0.12*abs(max(maxline,maxline-minline)))
            except ValueError:
                print('val error')

        #fig.canvas.draw()
        #ofig.canvas.draw()
        #ofig.canvas.flush_events()

    def onpick(self,event):
        # on the pick event, find the orig line corresponding to the
        # legend proxy line, and toggle the visibility
        #legline = event.artist
        b=False
        ar=self._axes
        fig=ar.legend_.figure
        for origline, legline in zip(ar.lines, ar.legend_.get_lines()):
            if legline==event.artist:
                #origline = lined[legline]
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
                b=True
                break
        if b:
            self.update_limit(ar,fig,origline.figure, ar.lines)
            if USEQT:
                fig.canvas.draw()  # draw
        else:
            print("onpick failed")
        #self._ax=
    def show_hide(self,toshow):
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
            fig.canvas.draw()#draw
