import datetime

from common.common import InputSourceType, UseCache

TZINFO=datetime.timezone(datetime.timedelta(hours=-3),'GMT3')
MAXCACHETIMESPAN=datetime.timedelta(days=1)
HIST_F = r'hist_file.cache'
PORT = 4001#5050
EXT=['QQQ']
DEF_FIG_SIZE = (13.2,6)
GROUPS= {'Tech': ['NVDA', 'AMD', 'CLOU', ]
        , 'FANG': ['FB', 'AAPL', 'GOOGL', 'AMZN']
        , 'Crypto': ['ethereum', 'cardano', 'bitcoin']
        , 'BroadEconomics': ['VO', 'VPU', 'GSG', ]
        , 'Alt Stocks': [ 'MSOS', 'MAC','ARKG', 'ARKK']
        , 'China': ['ADRE']
        , 'Europe': ['EWA', 'EWG', 'EZU', 'EDEN']
        , 'Money Others': ['TGT' 'FVRR', 'SQ', 'TSLA'],
        'Pharma': ['NVAX', 'BNTX', 'MRNA', 'REGN']}
EXCHANGES= ["nasdaq","xetra",'NYSE','OTC Markets']
EXCHANGES= [i.lower() for i in EXCHANGES]
INPUTSOURCE=InputSourceType.InvestPy
FN= r'prot2.csv'
DEF_PORTFOLIO = 'My Portfolio'
CACHEUSAGE=UseCache.USEIFAVALIABLE
