import datetime


'''
Config file for your project.

All the mentioned files here can take an absolute path. But if not, then config/config.py looks for them in  
'./data/', os.curdir, "~/MYPROJ", "/etc/"+MYPROJ, $PROJPATHENV

This is true also for myconfig.py.
'''

import datetime
import pytz

from common.common import InputSourceType, UseCache, VerifySave,CombineStrategy
IGNORECONF = {} # sym : fromdate
COMBINEDATEDIFF=20
COMBINEAMOUNTPERC=10

REGULAR_ACCOUNT = '' #your interactive broker account
REGULAR_USERNAME = '' #your username

TRANSACTION_HANDLERS={
    "StockPrices": {
        "Use":UseCache.USEIFAVALIABLE,
        "CacheSpan":datetime.timedelta(days=40),
        "File": r'stocksplit.cache',
        "IgnoreSymbols": set([])
           },
    "IB":
    {
        "File":r'ibtrans.cache',
        "CacheSpan": datetime.timedelta(hours=5),
        "Use": UseCache.USEIFAVALIABLE,
        "TryToQueryAnyway": False,
        "DOQUERY":True,
        "FLEXTOKEN":'YOURTOKEN',
        "FLEXQUERY" : 'QUERYNU'
    },
    "MyStocks":
    {
        "File":r'buydicnk.cache',
        # This is the file name of the portfolio. You may export the csv from my stocks portfolio.
        # https://play.google.com/store/apps/details?id=co.peeksoft.stocks&hl=iw&gl=US 
        # Or you can generate buy dictionary yourself...  
        "SrcFile": "example_mystock.csv",
        "PortofolioName": "My Portfolio",
        "Use": UseCache.USEIFAVALIABLE
    }
}

try:
    from transactions.transactioninterface import TransactionSourceType
    TRANSACTIONSOURCE = TransactionSourceType.IB | TransactionSourceType.MyStock
except:
    pass #ibsrv doesnt compile it

HOSTIB='127.0.0.1'
PORTIB=7596
IBSRVPORT=9091 #When you open IB SERVER in a sec process
ADDPROCESS= ['ibsrv.exe']
LOADLASTATBEGIN=True #Load last graph when the program starts 
ADDITIONALOPTIONS={} #Additonal graph options #{'marker':'o'}

LASTGRAPHNAME="Last"
IGNORE_ADJUST=1
SKIP_EARNINGS=1
TRYSTORAGEFOREARNINGS=1
DATAFILEPTR= 'DATA_FILE'
USEWX=0
USEWEB=0
USEQT=1
SIMPLEMODE=0 #in this mode, there is no UI, just graph. can set USEQT =0 only if  in simple mode.
DEFAULTCURR=["USD","EUR","GBP","ILS"]
TZINFO=datetime.timezone(datetime.timedelta(hours=-3),'GMT3')
MAXCACHETIMESPAN=datetime.timedelta(days=1)
HIST_F = r'hist_file.cache'
HIST_F_BACKUP = HIST_F+'.back'
DEFAULTNOTEBOOK=r'jupyter\defaultnotebook.ipynb'
PORT = 4001#5050
EXT=['QQQ']
DEF_FIG_SIZE = (13.2 * 0.5 ,6* 0.5)
EXCHANGES= ["NYSE","nasdaq","xetra",'NYSE','London','OTC Markets']
EXCHANGES= [i.lower() for i in EXCHANGES]
VALIDEXCHANGES=["NYSE","NASDAQ","ISLAND","XERTA","LSE"]
TRANSLATE_EXCHANGES={'NASDAQ':'NYSE'}


#Please use timezone aware value here!!
DEFAULTFROMDATE = datetime.datetime(2020,1,1,tzinfo=pytz.UTC)

'''
Define currencies for exchanges... 
'''
EXCHANGE_CURRENCY= {'London':'GBP','Xetra': 'EUR'}
'''
Define Currency for custom stocks. Use original name.  
'''
STOCK_CURRENCY= {'VETH.DE':'EUR','VBTC1':'EUR'}

INPUTSOURCE=InputSourceType.IB #IB for interactive

MINCOLFORCOLUMS=20
MIN=4000
MAXCOLS=30
MINCHECKREQ=10
MINIMALPRECREQ=0.2
CACHEUSAGE=UseCache.FORCEUSE
DOWNLOADDATAFORPROT=True
JSONFILENAME=r'groups.json'
SERIALIZEDFILE=r'serialized.dat' #internal
EARNINGSTORAGE = 'earnings.dat'
TRYSTORAGEFOREARNINGS= True



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
GRAPHFN='graphs.json'

BASECUR="USD"

REVENUEFILE ='NOEARNINGS'
INCOMEFILE = 'NOEARNINGS'
COMMONSTOCK= 'NOEARNINGS'

IGNORED_SYMBOLS=['FB']
#Rapid API of StockPrices  https://rapidapi.com/alphawave/api/stock-prices2/
#Used to get stock split history

StockPricesHeaders = {
    "X-RapidAPI-Host": "stock-prices2.p.rapidapi.com",
    "X-RapidAPI-Key": None 
}
SEEKINGALPHAHeaders = {
    "X-RapidAPI-Host": "seeking-alpha.p.rapidapi.com",
    "X-RapidAPI-Key": None
}
EXPORTEDPORT="exported.csv"
BOTHSYMBOLS=[]
MAXPERCDIFFIBSTOCKWARN=0.2
FIXBUYSELLDIFFDAYS=3
NORMALIZE_ON_TRANSACTIONSAVE=0
DONT_RUN_NOTEBOOK=False
STOP_EXCEPTION_IN_DEBUG=True
VERIFY_SAVING = VerifySave.Ask
CHECKRELOADINTERVAL=30
COMBINESTRATEGY=CombineStrategy.PREFERSTOCKS
IGNORECONF = {} # sym : fromdate
LOGFILE='log.txt'
LOGERRORFILE='error.log'
VOILA_PYTHON_PROCESS_PATH=None #The path of voila. Use if not running inside python.
AUTO_RESOVLE_VOILA_PYTHON=True
