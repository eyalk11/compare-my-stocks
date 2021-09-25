import datetime

MAXCACHETIMESPAN=datetime.timedelta(days=1)
HIST_F = r'hist_file.cache'
REGULAR_ACCOUNT = 'Account Number in IB'
REGULAR_USERNAME = 'User name in ib'
PORT = 5050
GROUPS= {'Chips': ['NVDA', 'AMD', 'CLOU', 'ARKG', 'ARKK']
        , 'FANG': ['FB', 'AAPL', 'GOOGL', 'AMZN']
        , 'crypt': ['ethereum', 'cardano', 'bitcoin']
        , 'broadec': ['VO', 'VPU', 'GSG', ]
        , 'anotherus': [ 'MSOS', 'MAC']
        , 'china': ['ADRE']
        , 'europe': ['EWA', 'EWG', 'EZU', 'EDEN']
        , 'moneyothers': ['TGT' 'FVRR', 'SQ', 'TSLA'],
              'med': ['NVAX', 'BNTX', 'MRNA', 'REGN']}
DEF_PORTFOLIO = 'My Portfolio'
FN="Csv From MyStockProtofolio (buy/sells)"