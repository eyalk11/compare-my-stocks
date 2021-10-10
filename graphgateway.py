import locale

from common import Types, config
from common import USEWX,USEWEB,USEQT
from compareengine import CompareEngine
#import mplfinance

from ib.ibtest import main as ibmain

locale.setlocale(locale.LC_ALL, 'C')


if __name__=='__main__':
    if USEWX:

        import wx
        app = wx.App()
        frame = wx.Frame(parent=None, title='Hello World')
        frame.Show()

#
import matplotlib


PROFITPRICE= Types.PROFIT | Types.ABS

def initialize_graph_and_ib():
    if USEWX:
        matplotlib.use('WxAgg')
    elif USEWEB:
        matplotlib.use('WebAgg')
    elif USEQT:
        matplotlib.use('QtAgg')
    else:
        matplotlib.use('TKAgg')
    ibmain(False)
    gg = CompareEngine(config.FN)
    return  gg

#fig.canvas.draw()
if __name__=='__main__':
    gg=initialize_graph_and_ib()
    #interactive(True)
    #gg.gen_graph()

    x= {'groups': ['FANG'],
 'type': Types(641),
 'compare_with': 'QQQ',
 'mincrit': 0,
 'maxnum': 0}

    gg.gen_graph(**x)
    #gg.gen_graph(type=Types.PRICE | Types.COMPARE,compare_with='QQQ', mincrit=-100000, maxnum=4000, groups=["FANG"],  starthidden=0)
    #gg.gen_graph(type=Types.VALUE, isline=True,groups=['broadec'],mincrit=-100000,maxnum=4000,use_cache=UseCache.FORCEUSE)
    #gg.update_graph(type=Types.PROFIT)
    #plt.show(block=True)
    a=1
    #getch()






