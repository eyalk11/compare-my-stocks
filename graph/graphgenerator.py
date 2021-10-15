import math
from functools import partial

import matplotlib
import mplcursors
from matplotlib import pyplot as plt
import numpy
from config import config
from common.common import USEQT
from common.common import Types
plt.rcParams["figure.autolayout"] = False


def show_annotation(sel,cls=None, ax=None):
    xi = sel.target[0]
    vertical_line = ax.axvline(xi, color='red', ls=':', lw=1)
    sel.extras.append(vertical_line)

    val=[  ( round(numpy.interp(xi, ll._x, ll._y),2),ll._visible,ll==sel[0])  for ll in ax.lines ]
    names= [ k._label for k in ax.legend_.legendHandles  ]
    annotation_str = '\n'.join([    ('%s' if not targ else r' $\bf{ %s }$')  % (f'{n}: {v1}') for n,(v1,vis,targ) in zip(names,val) if vis and not math.isnan(v1)  ])
    annotation_str+='\n'+str(matplotlib.dates.num2date(xi).strftime('%Y-%m-%d'))

    sel.annotation.set_text(annotation_str)
    #cls._annotation+=ann

class GraphGenerator:
    def __init__(self):
        self.params = None
        self._linesandfig=[]
        self.last_stock_list=set()
        self.cur_shown_stock=set()
        self.adjust_date=False

    def gen_actual_graph(self, B, cols, dt, isline, starthidden, just_upd,type):
        if not just_upd:
            self.cur_shown_stock = set()
        if just_upd:
            #plt.cla()
            #for ann in self._annotation:
            #    ann.remove()
                #del ann
            for child in plt.gca().get_children():
                if isinstance(child, matplotlib.lines.Line2D):
                    child.remove()
                if isinstance(child, matplotlib.text.Annotation):
                    child.remove()
            ar= self._linesandfig[-1][2]
            if  getattr(self,'cursor',None):
                self.cursor.disconnect('add',cb=self.cb)
                del self.cursor
            #mplfinance.plot(dt,figsize=(16, 10), reuse_plot=True,ax=ar,type='candle')
            dt.plot.line(figsize=config.DEF_FIG_SIZE, reuse_plot=True, ax=ar)
            #ar.legend_.figure.canvas.clear()
            #ar.legend_.figure.canvas.draw()
        else:

            if not isline:
                ar = dt.plot.area(figsize=config.DEF_FIG_SIZE, stacked=False)
            else:
                #mplfinance.plot(dt, figsize=(16, 10), type='candle')
                ar = dt.plot.line(figsize=config.DEF_FIG_SIZE)
        FACy = 1.2
        FACx = 2.4
        box = ar.get_position()
        ar.set_position([0, box.y0, 6*FACx, box.height])
        mfig = ar.figure
        st=''
        if type & Types.RELTOMAX:
            st = 'Precentage Down from Max Of '
        if type & Types.PRECENTAGE:
            st = 'Precentage Change In '
        if type & Types.DIFF:
            st = 'Change In '
        if type & Types.PROFIT:
            st += 'Profit'
        if type & Types.VALUE:
            st += 'Value'
        if type & Types.PRICE:
            st += 'Stock Price'
        if type & Types.COMPARE:
            st += ' Compared To ' + self.params.compare_with
        ar.set_title(st)

        # match type:
        #     case type if type & Types.RELTOMAX:
        #         st = 'Precentage Down from Max of '
        #     case type if type & Types.PRECENTAGE:
        #         st='Precentage Change of '
        #     case type if type & Types.DIFF:
        #         st = 'Change of '
        #     case type if type & Types.PROFIT:
        #         st+= 'Profit'
        #     case type if type & Types.VALUE:
        #         st+='Value'
        #     case type if type & Types.PRICE:
        #         st += 'Stock Price'
        #ar.set_title(st)


        mfig.set_size_inches(config.DEF_FIG_SIZE)
        #nice hack
        def set_fig_size(my,def_fig_size,*args,**kwargs):
            my.figsize= def_fig_size  #if anyone asks
        mfig.set_size_inches=partial(set_fig_size, mfig, config.DEF_FIG_SIZE)


        #ar.set_size_inches(15.1,6.46)#(7*FACx, hi * 0.6*FACy)

        # Put a legend to the right of the current aris
        if len(cols) >= config.MINCOLFORCOLUMS:

            ar.legend(loc='center left', bbox_to_anchor=B, ncol=len(cols) // config.MINCOLFORCOLUMS, handleheight=2.4, labelspacing=0.05)
        else:
            ar.legend(loc='center left', bbox_to_anchor=B,handleheight=2.4, labelspacing=0.05)
        if isline:
            (lined, fig) = self.handle_line(ar, starthidden,just_upd)

        if self.params.increase_fig or len(self._linesandfig)==0:
            # plt.figure(len(self.graphs))
            if isline:
                self._linesandfig += [(lined, fig,ar)]
        else:
            if isline:
                self._linesandfig[-1] = (lined, fig,ar)
        if 1:
            plt.gcf().autofmt_xdate()

             #plt.subplots_adjust(right=0.9)
            #plt.tight_layout(rect=[0, 0, 0.9, 1])
            ax=ar
            #ax.set_ylim(auto=True)
            ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%Y-%m-%d'))
            #ax.xaxis.set_major_formatter(plt.FuncFormatter(hhmmss_formatter))  # show x-axis as hh:mm:ss
            #ax.xaxis.set_major_locator(plt.MultipleLocator(2 * 60 * 60))  # set ticks every two hours

            self.cursor = mplcursors.cursor(hover=True)
            self.cb= self.cursor.connect('add', partial(show_annotation,cls=self,ax=ar))
            plt.grid(visible=True)
            #self._ax=ax
            if just_upd:
                #with self._out:

                self.update_limit(ar, fig, mfig, lined.values())
                if self.adjust_date:
                    f,t = plt.xlim()
                    fromdateNum = matplotlib.dates.date2num(self.params.fromdate) if self.params.fromdate else f
                    todateNum = matplotlib.dates.date2num(self.params.todate) if self.params.todate else t
                    plt.xlim([fromdateNum,todateNum])
                    plt.grid(b=True)
                    self.adjust_date=False
                    #plt.draw()
            elif self.params.show_graph:
                print('strange')
                pass#plt.show()
                    #from IPython.core.display import display
                    #display(mfig)
                    #plt.gcf().set_size_inches(13.57,  5.8 )
                    #plt.show()
            #else:
            #    plt.draw()
                #plt.show(block=False)
            #print('aftershow')
        #time.sleep(2)

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


        if just_upd:
            fig.canvas.mpl_disconnect(self.cid)
            fig.canvas.flush_events()
        self.cid=fig.canvas.mpl_connect('pick_event',partial(GraphGenerator.onpick,self) )
        for origline, legline in zip(ar.lines, leg.get_lines()):
            legline.set_picker(5)  # 5 pts tolerance
            lined[legline] = origline
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
        try:
            maxline = -100000000000
            minline = 100000000000
            for l in lines:
                if l.get_visible():
                    y = list(filter(lambda x: not math.isnan(x), l._y))
                    # x = list(filter(lambda x:not math.isnan(x) , l._x))
                    maxline = max(maxline, max(y))
                    minline = min(minline, min(y))
            ar.set_ylim(ymin=minline-0.12*abs(max(minline,maxline-minline)), ymax=maxline+0.12*abs(max(maxline,maxline-minline)))
        except ValueError:
            print('val error')

        #fig.canvas.draw()
        #ofig.canvas.draw()
        #ofig.canvas.flush_events()

    def onpick(self,event):
        # on the pick event, find the orig line corresponding to the
        # legend proxy line, and toggle the visibility
        legline = event.artist
        b=False

        for lined, fig,ar in self._linesandfig:
            if legline in lined:
                origline = lined[legline]
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
        if b:
            self.update_limit(ar,fig,origline.figure, lined.values())
            if USEQT:
                fig.canvas.draw()  # draw
        else:
            print("onpick failed")
        #self._ax=
    def show_hide(self,toshow):
        ar = self._linesandfig[-1][2]
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
