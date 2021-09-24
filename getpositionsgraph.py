import datetime
import inspect
import math
import locale
import time

from ibtest import main,get_symbol_history

locale.setlocale(locale.LC_ALL, 'C')

USEWX=0
USEWEB=0

if __name__=='__main__':
    if USEWX:

        import wx
        app = wx.App()
        frame = wx.Frame(parent=None, title='Hello World')
        frame.Show()
        #app.MainLoop()
        #locale = wx.Locale(wx.LANGUAGE_ENGLISH_US)


#
from math import floor
from msvcrt import getch
from enum import Flag, auto
import matplotlib
import pandas as pd
from collections import defaultdict
import mplcursors

from matplotlib import interactive
import numpy
#interactive(True)
import matplotlib.pyplot as plt
from functools import partial

from orederedset import OrderedSet
plt.rcParams["figure.autolayout"] = False
FN = r'C:\Users\ekarni\Downloads\logs-insights-results (6).csv'
#matplotlib.use('WebAgg')
#plt.rcParams['figure.constrained_layout.use'] = True

MIN=4000
MAXCOLS=30
MINCOLFORCOLUMS=80

#pd.DataFrame()
class MyOrderedSet(OrderedSet):
    def intersection(self,set):
        l=OrderedSet()
        for k in self:
            if k in set:
                l.add(k)
        return l

import collections
from orederedset import  *

linesandfig=[]

from enum import Flag,auto
class Types(Flag):
    PRICE=1
    VALUE=auto()
    PROFIT = auto()
    ABS= auto()
    RELTOMAX=auto()
    PRECENTAGE=auto()
    DIFF=auto()
    COMPARE=auto()


PROFITPRICE= Types.PROFIT | Types.ABS


def show_annotation(sel,cls=None, ax=None):
    xi = sel.target[0]
    vertical_line = ax.axvline(xi, color='red', ls=':', lw=1)
    sel.extras.append(vertical_line)

    val=[  ( str(round(numpy.interp(xi, ll._x, ll._y),2)),ll._visible,ll==sel[0])  for ll in ax.lines ]
    names= [ k._legmarker._label for k in ax.legend_.legendHandles  ]
    annotation_str = '\n'.join([    ('%s' if not targ else r' $\bf{ %s }$')  % (f'{n}: {v1}') for n,(v1,vis,targ) in zip(names,val) if vis  ])
    annotation_str+='\n'+str(matplotlib.dates.num2date(xi).strftime('%Y-%m-%d'))

    sel.annotation.set_text(annotation_str)
    #cls._annotation+=ann


class MyGraphGen:
    Groups = {'Chips': ['NVDA', 'AMD', 'CLOU', 'ARKG', 'ARKK']
        , 'FANG': ['FB', 'AAPL', 'GOOGL', 'AMZN']
        , 'crypt': ['ethereum', 'cardano', 'bitcoin']
        , 'broadec': ['VO', 'VPU', 'GSG', ]
        , 'anotherus': [ 'MSOS', 'MAC']
        , 'china': ['ADRE']
        , 'europe': ['EWA', 'EWG', 'EZU', 'EDEN']
        , 'moneyothers': ['TGT' 'FVRR', 'SQ', 'TSLA'],
              'med': ['NVAX', 'BNTX', 'MRNA', 'REGN']}


    def __init__(self,filename,o):
        self._fn=filename
        self._alldates=None
        self._fset=set()
        self._linesandfig=[]
        self._annotation=[]
        t=inspect.getfullargspec(MyGraphGen.gen_graph)
        [self.__setattr__(a, d) for a, d in zip(t.args, t.defaults)]
        self._out=o
        self.cur_shown_stock=set()
        self.last_stock_list=set()


    def getli(self, mincrit, div=Types.RELTOMAX,compare_with=None):

        flist=sorted(self._fset)

        if div & Types.PROFIT:
            dic=self._allprofit
        elif div & Types.PRICE:
            dic = self._price
        else: #value
            dic=self._alldates


        #dic=dic.deepcopy()
        compit = dic[compare_with]#dic.pop(compare_with)

        for st, v in dic.items():
            ign = False
            if div & Types.COMPARE:
                v= { f: v[f]- compit[f] for f in flist}
                if div& Types.PRECENTAGE:
                    v = {f : (v[f] / compit[f]) * 100 for f in flist}
                    ign=True
            maxon=[l for l in v.values() if not math.isnan(l)]
            if len(maxon)==0:
                return
            M = max(maxon)

            if div & Types.RELTOMAX:
                values = [(v[f] / M)*100 for f in flist]
            elif div & Types.ABS:
                values = [v[f] for f in flist]
            elif div & Types.PRECENTAGE and not ign:
                t=flist[0]
                values= [(v[f]/t)*100 for f in flist ]
            elif div & Types.DIFF:
                t=flist[0]
                values= [(v[f]-t) for f in flist ]
            else:
                values = [v[f] for f in flist] #ABS is the default

            if M > mincrit:
                yield st, values, M
            else:
                pass #print('ignoring ', st)

    def process_file(self,fromdate=None,todate=None):
        self._alldates =defaultdict(lambda: defaultdict(lambda:numpy.NaN ))
        self._allprofit = defaultdict(lambda: defaultdict(lambda:numpy.NaN ))
        self._price=defaultdict(lambda: defaultdict(lambda:numpy.NaN ))

        self._fset = set()

        qtydic= defaultdict(lambda: defaultdict(lambda:numpy.NaN ))

        lines=list([x.replace('\n','').replace('\r','') for x in open(self._fn)])[1:]
        #lines=
        lst=list(zip(lines,lines[1:]))
        getf =( fromdate==None)
        gett = ( todate==None)

        for i in range(0,len(lines),2):
            arr=lst[i]
            #lst.next()
            #arr= l.split(',')
            date_time_obj = datetime.datetime.strptime( arr[1][2:], '%Y-%m-%d %H:%M:%S.%f')
            if fromdate==None:
                fromdate=date_time_obj
            elif date_time_obj<fromdate:
                fromdate=date_time_obj
            if todate == None:
                todate = date_time_obj
            elif date_time_obj > todate:
                todate = date_time_obj

            l=arr[0]
            if not 'TotProfit' in l:
                #print(arr[1])
                continue
            #l=arr[1]
            l=l[l.index(',')+2:]


            if l.startswith('{'):
                t = l[:-1]
                dic = eval(t)
                dic = dic
                if fromdate and date_time_obj<fromdate:
                    continue
                if  todate and date_time_obj > todate:
                    continue
                form = matplotlib.dates.date2num(date_time_obj)
                self._fset.add(form)
                for k, v in dic.items():
                    if type(v) == dict:
                        qtydic[k][form]=v['Qty']


        #diff=todate-fromdate
        ll=datetime.now - fromdate
        for k,dic in qtydic.items():
            lastv=None
            diffdic={}
            for f in sorted(list(dic.keys())):
                if not math.isnan(dic[f]):
                    lastv=dic[f]
                if math.isnan(dic[f]) and lastv!=None:
                    dic[f]=lastv

                diffdic[f]




            hist = get_symbol_history(k, '%sd' % ll.days,'1d'  ) #should be rounded
            for l in hist:

                #if l['t']>todate:
                #    break
                tim=l[t]
                if
        for day in range(diff.days+1  ):






            self._alldates[k][form] = v['Value']
            self._allprofit[k][form]= v['TotProfit']
            self._price[k][form] = v['CurAvg'] if 'CurAvg' in v else v['Open']
#
    # def process_file(self,fromdate=None,todate=None):
    #     self._alldates =defaultdict(lambda: defaultdict(lambda:numpy.NaN ))
    #     self._allprofit = defaultdict(lambda: defaultdict(lambda:numpy.NaN ))
    #     self._fset = set()
    #
    #     for l in open(self._fn):
    #         if l.startswith('"{'):
    #             t = l[1:-1]
    #             dic = eval(t)
    #             dic = dic
    #             if fromdate and dic['TIME']<fromdate:
    #                 continue
    #             if  todate and dic['TIME'] > todate:
    #                 continue
    #             form = matplotlib.dates.date2num( dic['TIME'])
    #             self._fset.add(form)
    #             for k, v in dic.items():
    #                 if type(v) == dict:
    #                     self._alldates[k][form] = v['CurAvg'] * v['OldQty']


    def gen_graph(self,groups=None ,mincrit=MIN,maxnum=MAXCOLS,type=Types.VALUE,ext=['QQQ'],increase_fig=1,fromdate=None,todate=None,isline=True,starthidden=1,compare_with=None,reprocess=1,just_upd=0,shown_stock=set()):
        t = inspect.getfullargspec(MyGraphGen.gen_graph)
        for a in t.args:
            self.__setattr__(a, locals()[a])
        B = (1, 0.5)
        if reprocess:
            self.process_file(fromdate,todate)
        odata = list(self.getli( mincrit, type,compare_with))
        odata.sort(key=lambda x: x[2])
        data = odata[(-1) * maxnum:]
        ll=[x[0] for x in data]
        cols = MyOrderedSet(ll)
        self.cols=cols
        if groups:
            curse=set()
            for g in groups:
                curse=curse.union( set(self.Groups[g]))
            cols=cols.intersection(curse)
        for sym in ext:
            if not sym in cols:
                data += [(k, x, y) for k, x, y in odata if k == sym]
                cols.add(sym)
        data = {x: y for (x, y, z) in data}
        dt = pd.DataFrame(data, columns=cols, index=[  matplotlib.dates.num2date(y) for y in self._fset])

        self.gen_actual_graph(B, cols, dt, increase_fig, isline, starthidden,just_upd,type)

    def update_graph(self,**kwargs):
        reprocess= 1 if  (set(['fromdate','todate']).intersection(set(kwargs.keys())) or not self._alldates) else 0
        for k in kwargs:
            if k in self.__dict__:
                self.__dict__[k]=kwargs[k]
        t = inspect.getfullargspec(MyGraphGen.gen_graph)
        dd={x:self.__getattribute__(x) for x in t.args if x not in ['self','increase_fig','reprocess','just_upd' ] }
        self.gen_graph( increase_fig = 0,reprocess=reprocess,just_upd=1,**dd )






    def gen_actual_graph(self, B, cols, dt, increase_fig, isline, starthidden, just_upd,type):
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
            self.cursor.disconnect('add',cb=self.cb)
            del self.cursor
            dt.plot.line(figsize=(16, 10), reuse_plot=True,ax=ar)
            #ar.legend_.figure.canvas.clear()
            #ar.legend_.figure.canvas.draw()
        else:

            if not isline:
                ar = dt.plot.area(figsize=(15.1,6.46), stacked=False)
            else:
                ar = dt.plot.line(figsize=(13.2, 6))
        FACy = 1.2
        FACx = 2.4
        box = ar.get_position()
        ar.set_position([0, box.y0, 6*FACx, box.height])
        mfig = ar.figure
        st=''
        if type & Types.RELTOMAX:
            st = 'Precentage Down from Max of '
        if type & Types.PRECENTAGE:
            st = 'Precentage Change of '
        if type & Types.DIFF:
            st = 'Change of '
        if type & Types.PROFIT:
            st += 'Profit'
        if type & Types.VALUE:
            st += 'Value'
        if type & Types.PRICE:
            st += 'Stock Price'
        if type & Types.COMPARE:
            st += ' Compared To ' + self.compare_with
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


        #wi, hi = mfig.get_size_inches()
        mfig.set_size_inches(13.2, 6)
        #ar.set_size_inches(15.1,6.46)#(7*FACx, hi * 0.6*FACy)

        # Put a legend to the right of the current aris
        if len(cols) >= MINCOLFORCOLUMS:

            ar.legend(loc='center left', bbox_to_anchor=B, ncol=len(cols) // MINCOLFORCOLUMS,handleheight=2.4, labelspacing=0.05)
        else:
            ar.legend(loc='center left', bbox_to_anchor=B,handleheight=2.4, labelspacing=0.05)
        if isline:
            (lined, fig) = self.handle_line(ar, starthidden,just_upd)
        if increase_fig or len(self._linesandfig)==0:
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
            #self._ax=ax
            if just_upd:
                with self._out:
                    plt.grid()
                self.update_limit(ar, fig, mfig, lined.values())
            if not just_upd:

                with self._out:
                    mfig.set_size_inches(13.2, 6)
                    plt.grid()
                    plt.show()
                    #from IPython.core.display import display
                    #display(mfig)
                    #plt.gcf().set_size_inches(13.57,  5.8 )
                    #plt.show()
            #else:
            #    plt.draw()
                #plt.show(block=False)
            #print('aftershow')
        #time.sleep(2)
        mfig.set_size_inches(13.2, 6)

    def show_hide(self,toshow):
        ar = self._linesandfig[-1][2]
        leg = ar.legend_
        fig = leg.figure
        for origline, legline in zip(ar.lines, leg.get_lines()):
            if toshow:
                legline.set_alpha(0.2)
                origline.set_visible(0)
            else:
                legline.set_alpha(1)
                origline.set_visible(1)
        #fig.canvas.draw()

    def handle_line(self,ar,starthidden,just_upd):
        lined=dict()
        leg = ar.legend_
        fig = leg.figure
        nlst = set([x._legmarker._label for x in leg.get_lines()])
        if self.last_stock_list!=nlst:
            if self.last_stock_list<nlst or (self.cur_shown_stock!=self.cur_shown_stock.intersection(nlst)): #if there are more stocks , or we removed a stock that was shown
                self.cur_shown_stock=set()



        istrivial=( len(self.shown_stock)==0 or len(self.shown_stock)==len(ar.lines))
        iscurtrivial = (len(self.cur_shown_stock) == 0 or len(self.cur_shown_stock) == len(ar.lines))
        if (iscurtrivial and starthidden):
            self.cur_shown_stock=set()
        if not istrivial:
            self.cur_shown_stock=self.shown_stock


        if just_upd:
            fig.canvas.mpl_disconnect(self.cid)
            fig.canvas.flush_events()
        self.cid=fig.canvas.mpl_connect('pick_event',partial(MyGraphGen.onpick,self) )
        for origline, legline in zip(ar.lines, leg.get_lines()):
            legline.set_picker(5)  # 5 pts tolerance
            lined[legline] = origline
            if not istrivial:
                hide=   legline._legmarker._label not in self.shown_stock #act based on shown_stock
            else:
                hide=  (iscurtrivial and starthidden) or (not iscurtrivial and   (legline._legmarker._label not in self.cur_shown_stock))

            if hide:
                legline.set_alpha(0.2)  # hide
                origline.set_visible(0)
            else:
                self.cur_shown_stock.add(legline._legmarker._label) #maybe there
                legline.set_alpha(1)  # hide
                origline.set_visible(1)
        self.last_stock_list = nlst
        return (lined, fig)

    def update_limit(self,ar,fig,ofig,lines):
        maxline = -100000000000
        minline = 100000000000
        for l in lines:
            if l.get_visible():
                y = list(filter(lambda x: not math.isnan(x), l._y))
                # x = list(filter(lambda x:not math.isnan(x) , l._x))
                maxline = max(maxline, max(y))
                minline = min(minline, min(y))
        ar.set_ylim(ymin=minline, ymax=maxline)
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
                    self.cur_shown_stock.add(legline._legmarker._label)
                else:
                    legline.set_alpha(0.2)
                    self.cur_shown_stock.remove(legline._legmarker._label)
            b=True
        if b:
            self.update_limit(ar,fig,origline.figure, lined.values())
        #self._ax=






#fig.canvas.draw()
if __name__=='__main__':
    main(False)
    gg=MyGraphGen(FN,open('a.t','w'))
    if USEWX:
        matplotlib.use('WxAgg')
    elif USEWEB:
        matplotlib.use('WebAgg')
    else:
        matplotlib.use('TKAgg')
    #interactive(True)
    #gg.gen_graph()

    x= {'group': ('FANG',),
     'type': 196,
     'compare_with': 'QQQ',
     'mincrit': 0,
     'maxnum': 0}

    gg.gen_graph(**x)
    #gg.gen_graph(type=Types.PRICE | Types.COMPARE,compare_with='QQQ', mincrit=-100000, maxnum=4000, groups=["FANG"],  starthidden=0)
    #gg.gen_graph(type=Types.VALUE, isline=True,groups=['broadec'],mincrit=-100000,maxnum=4000)
    #gg.update_graph(type=Types.PROFIT)
    #plt.show(block=True)
    a=1
    #getch()
#import matplotlib.pyplot as plt
#plt.plot(ar)
#plt.show()
#lis= map(lambda x:x[1],lis)





