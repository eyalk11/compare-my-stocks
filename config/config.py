import datetime

from common.common import InputSourceType, UseCache



import datetime

from common.common import InputSourceType, UseCache

USEWX=0
USEWEB=0
USEQT=1
SIMPLEMODE=0 #in this mode, there is no UI, just graph. can set USEQT =0 only if  in simple mode.
DEFAULTCURR=["USD","EUR","GBP","ILS"]
TZINFO=datetime.timezone(datetime.timedelta(hours=-3),'GMT3')
MAXCACHETIMESPAN=datetime.timedelta(days=1)
HIST_F = r'hist_file.cache'
HIST_F_BACKUP = HIST_F+'.back'
BUYDICTCACHE=r'mybuydicn.cache'
REGULAR_ACCOUNT = '' #your interactive broker account
REGULAR_USERNAME = '' #your username
PORT = 4001#5050
EXT=['QQQ']
DEF_FIG_SIZE = (13.2,6)
EXCHANGES= ["nasdaq","xetra",'NYSE','London','OTC Markets']
EXCHANGES= [i.lower() for i in EXCHANGES]

'''
Define currencies for exchanges... 
'''
EXCHANGE_CURRENCY= {'London':'GBP','Xetra': 'EUR'}
'''
Define Currency for custom stocks. Use original name.  
'''
STOCK_CURRENCY= {'VETH.DE':'EUR','VBTC1':'EUR'}

INPUTSOURCE=InputSourceType.InvestPy
FN = r''
#FN= r'C:\Users\ekarni\mypy\prot2.csv'
DEF_PORTFOLIO = 'My Portfolio'
MINCOLFORCOLUMS=20
MIN=4000
MAXCOLS=30
MINCHECKREQ=10
MINIMALPRECREQ=0.2
CACHEUSAGE=UseCache.FORCEUSE
DOWNLOADDATAFORPROT=True
JSONFILENAME=r'.\config\mygroups.json'
SERIALIZEDFILE=r'.\myserialized.dat' #internal
'''
Translate Unknown stocks(in your protfolio) to known once..
'''
TRANSLATEDIC= {
        'VETHG.DE': "VETH",
        "VTBC.DE" : "VBTC1",
        "ADA-USD": "cardano",
        "VUKE.L" : "VUKE"
}
CRYPTO= set(['cardano','bitcoin','ethereum']) #names of investpy
DEBUG=1
GRAPHFN='mygraphs.json'

BASECUR="USD"

REVENUEFILE =None # r'C:\Users\ekarni\Downloads\tmpdat.json'
INCOMEFILE = None #r'C:\Users\ekarni\Downloads\tmpinc.json'
COMMONSTOCK= None #r'C:\Users\ekarni\Downloads\tmpcommonstock.json'