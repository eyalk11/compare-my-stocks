import pandas as pd
import csv
import random
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List
from enum import Enum, unique
from ibflex import Trade

@unique
class BuySellEnum(Enum):
    BUY = "BUY"
    CANCELBUY = "BUY (Ca.)"
    SELL = "SELL"
    CANCELSELL = "SELL (Ca.)"

def parse_trade(row):
    dt_format = "%Y%m%d"
    
    if 'FxPnl' in row and 'MtmPnl' in row:
        return Trade(
            tradeID=row['TradeID'],
            clientAccountID=row.get('ClientAccountID', ''),
            currencyPrimary=row['CurrencyPrimary'],
            symbol=row['Symbol'],
            conid=row.get('Conid', ''),
            securityID=row.get('SecurityID', ''),
            securityIDType=row.get('SecurityIDType', ''),
            underlyingConid=row.get('UnderlyingConid', ''),
            underlyingSymbol=row.get('UnderlyingSymbol', ''),
            underlyingSecurityID=row.get('UnderlyingSecurityID', ''),
            underlyingListingExchange=row.get('UnderlyingListingExchange', ''),
            putCall=row['Put/Call'],
            tradeDate=datetime.strptime(row['TradeDate'], dt_format).date(),
            transactionType=row.get('TransactionType', ''),
            exchange=row.get('Exchange', ''),
            quantity=Decimal(row['Quantity']),
            tradePrice=Decimal(row['TradePrice']),
            tradeMoney=Decimal(row.get('TradeMoney', 0)),
            netCash=Decimal(row.get('NetCash', 0)),
            costBasis=Decimal(row.get('CostBasis', 0)),
            fifoPnlRealized=Decimal(row.get('FifoPnlRealized', 0)),
            fxPnl=Decimal(row['FxPnl']),
            mtmPnl=Decimal(row['MtmPnl']),
            buySell=row['Buy/Sell'],
            ibOrderID=row.get('IBOrderID', ''),
            orderTime=row.get('OrderTime', ''),
            orderType=row.get('OrderType', ''),
            dateTime=datetime.strptime(row['DateTime'], "%Y%m%d;%H%M%S")
        )
    else:
        return Trade(
            tradeID=row.Index + 60000,
            currency=row['CurrencyPrimary'],
            fxRateToBase=Decimal(row['FxRateToBase']),
            symbol=row['Symbol'],
            strike=row.get('Strike', ''),
            expiry=row.get('Expiry', ''),
            putCall=row.get('Put/Call', ''),
            dateTime=datetime.strptime(row['DateTime'], dt_format)+timedelta(seconds=random.randrange(0,60),minutes=random.randrange(0,60)),
            tradeDate=datetime.strptime(row['DateTime'], dt_format).date(),
            quantity=Decimal(row['Quantity']),
            tradePrice=Decimal(row['TradePrice']),
            cost=Decimal(row['Cost']),
            fifoPnlRealized=Decimal(row['FifoPnlRealized']),
            fxPnl=Decimal(row['FxPnl']),
            buySell=row['Buy/Sell']
        )
def return_trades(filepath):
    df = pd.read_csv(filepath)
    trades = []
    for i, row in df.iterrows():
        trades.append(parse_trade(row))
    return trades


