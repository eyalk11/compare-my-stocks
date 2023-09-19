import matplotlib
import numpy

from config import config

st = ["A", "AAPL", "ABBV", "ABC", "ABMD", "ABT", "ADRE", "AFL", "AIG", "AIZ", "AJG", "ALGN", "ALL", "AMD", "AMGN",
      "AMP", "AMZN", "ANTM", "AON", "ARKG", "ARKK", "AXP", "BABA", "BAC", "BAX", "BDX", "BEN", "BIIB", "BIO", "BK",
      "BLK", "BMY", "BNTX", "BRK-B", "BRO", "BSX", "BUG", "C", "CAH", "CB", "CBOE", "CERN", "CFG", "CI", "CINF", "CLOU",
      "CMA", "CME", "CNC", "COF", "COO", "CRL", "CRWD", "CTLT", "CVS", "DFS", "DGP", "DGX", "DHR", "DVA", "DXCM", "EBS",
      "EDEN", "EMQQ", "ESYJY", "EW", "EWA", "EWG", "EZU", "FB", "FITB", "FRC", "FTNT", "FVRR", "FXP", "GILD", "GL",
      "GOOGL", "GS", "GSG", "HBAN", "HCA", "HIG", "HOLX", "HSIC", "HUM", "ICE", "IDXX", "ILMN", "INCY", "IQV", "ISRG",
      "IVZ", "JNJ", "JPM", "KEY", "KMDA", "L", "LH", "LIT", "LLY", "LNC", "MA", "MAC", "MCK", "MCO", "MDT", "MET",
      "MKTX", "MMC", "MRK", "MRNA", "MS", "MSCI", "MSFT", "MSOS", "MTB", "MTD", "NDAQ", "NET", "NTRS", "NVAX", "NVDA",
      "OGN", "PBCT", "PFE", "PFG", "PGR", "PKI", "PNC", "PRU", "PYPL", "QCOM", "QDEL", "QID", "QQQ", "RE", "REGN", "RF",
      "RHHBY", "RJF", "RMD", "SCHW", "SDS", "SIVB", "SNOW", "SPGI", "SPX", "SQ", "SQQQ", "STE", "STT", "SYF", "SYK",
      "TECH", "TFC", "TFX", "TGT", "TMICY", "TMO", "TROW", "TRV", "TSLA", "UHS", "UNH", "USB", "V", "VAW", "VETHG.DE",
      "VNQ", "VO", "VPU", "VRTX", "VTBC.DE", "VTRS", "VUKE.L", "WAT", "WBA", "WFC", "WLTW", "WRB", "WST", "WU", "XRAY",
      "ZBH", "ZION", "ZM", "ZS", "ZTS"]

import json
from collections import defaultdict
from dateutil import parser
from pandas import DataFrame


def getearnings_int(st, aa):
    dic = defaultdict(lambda: defaultdict(lambda: numpy.NaN))
    # df=DataFrame.from_records(aa)
    for x, y in zip(st, aa):
        if y != 'cccd' and y != 'aaa' and y!='bbb':
            for t in y:
                dat = parser.parse(t[0])
                dat=matplotlib.dates.date2num(dat)
                dic[x][dat] = t[1]
    return DataFrame.from_dict(dic)


def get_earnings():
    if config.Earnings.SKIP_EARNINGS:
        raise Exception("no earnings")
    aa = json.load(open(config.File.IncomeFile))
    bb = json.load(open(config.File.RevenueFile))
    cs= json.load(open(config.File.CommonStock))
    income = getearnings_int(st, aa)
    revenue = getearnings_int(st, bb)
    cs = getearnings_int(st,cs)
    return income, revenue,cs
