import locale

from common.common import Types
from common.common import USEWX
#import mplfinance
from engine.parameters import Parameters

from main import initialize_graph_and_ib

locale.setlocale(locale.LC_ALL, 'C')


if __name__=='__main__':
    if USEWX:

        import wx
        app = wx.App()
        frame = wx.Frame(parent=None, title='Hello World')
        frame.Show()

#


PROFITPRICE= Types.PROFIT | Types.ABS

#fig.canvas.draw()
if __name__=='__main__':
    gg= initialize_graph_and_ib()
    #interactive(True)
    #gg.gen_graph()

    x= {'groups': ['FANG'],
 'type': Types(641),
 'compare_with': 'QQQ',
 'mincrit': 0,
 'maxnum': 0}

    gg.gen_graph(Parameters(**x))
    #gg.gen_graph(type=Types.PRICE | Types.COMPARE,compare_with='QQQ', mincrit=-100000, maxnum=4000, groups=["FANG"],  starthidden=0)
    #gg.gen_graph(type=Types.VALUE, isline=True,groups=['broadec'],mincrit=-100000,maxnum=4000,use_cache=UseCache.FORCEUSE)
    #gg.update_graph(type=Types.PROFIT)
    #plt.show(block=True)
    a=1
    #getch()






