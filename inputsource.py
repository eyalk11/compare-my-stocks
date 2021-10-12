import datetime
from abc import ABC, abstractmethod

import config


class InputSource(ABC):
    @abstractmethod
    def get_symbol_history(self,sym,startdate,enddate):
        '''
        The right out format is dic[dates]['Open','Close'] and more ..
        :param sym:
        :param startdate:
        :param enddate:
        :return:
        '''
        pass

#Not working currently.
class IBSource(InputSource):

    def get_symbol_history(self,sym,startdate,enddate):
        ll = datetime.datetime.now(config.TZINFO) - startdate
        from ib.ibtest import get_symbol_history
        return get_symbol_history(sym, '%sd' % ll.days, '1d')


class InvestPySource(InputSource):

    def get_symbol_history(self, sym, startdate, enddate):
        try:
            import investpy
            l=None
            for l in investpy.search_quotes(text=sym,n_results=10):
                l=l.__dict__
                if l['exchange'].lower() in  config.EXCHANGES:
                    break
            else:
                if l:
                    print(f'not  right exchange {sym}, picking {l}' )
                else:
                    print('nothing for %s ' % sym )
                    return None
            if 1: #use my fork please
                df = investpy.get_etf_historical_data(etf=l['symbol'], country=l['country'], id=l['id_'],
                                                      from_date=startdate.strftime('%d/%m/%Y'),
                                                      to_date=enddate.strftime('%d/%m/%Y'))

            return l, { row[0].to_pydatetime():{j:row[1][j] for j in df} for row in df.iterrows()}
        except Exception as  r:
            print(f'{l if l else ""} is  {r}')
            return None