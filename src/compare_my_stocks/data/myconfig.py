import datetime


'''
Config file for your project.

All the mentioned files here can take an absolute path. But if not, then config/config.py looks for them in  
'./data/', os.curdir, "~/MYPROJ", "/etc/"+MYPROJ, $PROJPATHENV

This is true also for myconfig.py.
'''

import datetime
import pytz

from common.common import InputSourceType, UseCache
SKIP_EARNINGS=1
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
BUYDICTCACHE=r'mybuydicn.cache'
DEFAULTNOTEBOOK=r'jupyter\defaultnotebook.ipynb'
REGULAR_ACCOUNT = '' #your interactive broker account
REGULAR_USERNAME = '' #your username
PORT = 4001#5050
EXT=['QQQ']
DEF_FIG_SIZE = (13.2,6)
EXCHANGES= ["nasdaq","xetra",'NYSE','London','OTC Markets']
EXCHANGES= [i.lower() for i in EXCHANGES]

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

INPUTSOURCE=InputSourceType.InvestPy
'''
This is the file name of the portfolio. You may export the csv from my stocks portfolio.
https://play.google.com/store/apps/details?id=co.peeksoft.stocks&hl=iw&gl=US 
Or you can generate buy dictionary yourself...  
'''
PORTFOLIOFN = r'NOPORTFOLIO'
'''
The name of the portfolio in the file. 
'''
DEF_PORTFOLIO = 'My Portfolio'
MINCOLFORCOLUMS=20
MIN=4000
MAXCOLS=30
MINCHECKREQ=10
MINIMALPRECREQ=0.2
CACHEUSAGE=UseCache.FORCEUSE
DOWNLOADDATAFORPROT=True
JSONFILENAME=r'mygroups.json'
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

REVENUEFILE ='NOEARNINGS'
INCOMEFILE = 'NOEARNINGS'
COMMONSTOCK= 'NOEARNINGS'

IGNORED_SYMBOLS=[]
