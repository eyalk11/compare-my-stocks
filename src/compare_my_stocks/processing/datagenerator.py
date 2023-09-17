import datetime
import logging

import matplotlib
import numpy
import numpy as np
import pandas
from memoization import cached

from common.common import Types, UniteType, NoDataException, get_first_where_all_are_good, Serialized, \
    LimitType, log_conv
from config import config
from engine.compareengineinterface import CompareEngineInterface
from engine.symbolsinterface import SymbolsInterface
from input.inputprocessorinterface import InputProcessorInterface
from processing.actondata import ActOnData
from processing.datageneratorinterface import DataGeneratorInterface
from common.common import lmap 


class DataGenerator(DataGeneratorInterface):
    @property
    def params(self):
        return self._eng.params

    def __init__(self, eng: CompareEngineInterface):
        self._eng = eng
        self._inp : InputProcessorInterface = self._eng.input_processor
        # DataGenerator.minMaxChanged.initemit()
        self.colswithoutext = []
        self.tmp_colswithoutext = []
        self.after_filter_data = None
        self.minValue = None
        self.maxValue = None

        self.cols = None  # not exported by compareengine
        self.finalcols = None
        self.act = None

        self.used_unitetype = None
        self.to_use_ext = None
        self.data_generated = False
        self.df_before_act = None
        self.additional_dfs_fixed = None
        self.used_type=None 
        self.used_unitetype=None

    def get_data_by_type(self, type=Types.RELTOMAX, compare_with=None):
        params = self.generate_initial_data(compare_with, type)
        self.df_before_act = params[1].copy()
        act = ActOnData(*params, compare_with, self)
        self.act = act
        act.do()

        self.data_generated = True
        self.df , self.Marr, self.min_arr, self.type = act.df, act.Marr, act.min_arr, act.type

    def generate_initial_data(self, compare_with, type):
        fromdateNum = matplotlib.dates.date2num(self.params.fromdate) if self.params.fromdate else 0
        todateNum = matplotlib.dates.date2num(self.params.todate) if self.params.todate else float('inf')

        df, self.used_unitetype , self.additional_dfs = self.get_df_by_type(type, self.params.unite_by_group)
        self.orig_df = df
        self.used_type = type

        # self.to_use_ext = use_ext and self.params.use_ext
        self.to_use_ext = self.params.use_ext
        if (self.used_unitetype & ~UniteType.NONE):
            df, colswithoutext = self.unite_groups(df)  # in case really unite groups, colswithoutext is correct

        df = df[(df.index >= fromdateNum) * (df.index <= todateNum)]

        if self.used_type & Types.COMPARE:
            if not compare_with in df:
                logging.debug(('too bad, no compare'))
                self.used_type = self.used_type & ~Types.COMPARE

                # ind=first_index_of(compit_arr,np.isnan)
                # df=df.iloc[ind:]
        comp_set = (set([compare_with]) if self.used_type & Types.COMPARE else set())

        if not (self.params.unite_by_group & ~(UniteType.ADDTOTALS)):  # in unite, the compare_with is already there.
            # If the  unite is non-trivial, then colswithoutext already returned
            cols, colswithoutext = self.cols_by_selection(df)
            # if self.used_type & Types.COMPARE:
            fulldf = df[sorted(list(cols.union(comp_set)))]
        else:  # colswithoutext non-trivial
            fulldf = df
            cols = set(df.columns)
        #if fulldf is empty, raise exception
        if len(fulldf) == 0:
            raise NoDataException("Fulldf is empty")

            ##else we need everything...
        self.bef_rem_data = fulldf.copy()
        arr = np.array(fulldf).transpose()  # will just work with arr
        fulldf = fulldf.drop(list(
            df.index[list((np.all(np.isnan(arr), axis=0)))]))  # to check drop dates in which all stocks are none.

        self.use_relative = False
        if self.used_type & (Types.COMPARE | Types.PRECENTAGE | Types.DIFF):
            fullarr = np.array(fulldf).transpose()  # again...
            goodind = get_first_where_all_are_good(fullarr, self.used_type & Types.PRECENTAGE)
            if goodind == -1:
                logging.debug(('there is no location where all are good'))
                self.use_relative = True
            else:
                fulldf = fulldf.iloc[goodind:]
            if self.used_type & (Types.RELTOEND):
                goodind = get_first_where_all_are_good(fullarr, self.used_type & Types.PRECENTAGE, last=1)
                if goodind == -1:
                    logging.debug(('there is no location where all are good'))
                    self.use_relative = True
                else:
                    fulldf = fulldf.iloc[goodind:]

        df = fulldf[sorted(list(cols - comp_set))]
        arr = np.array(df).transpose()  # will just work with arr

        if len(arr) == 0:
            raise NoDataException("arr is empty")

        self.tmp_colswithoutext = set(colswithoutext).intersection(df.columns)
        self.after_filter_data = fulldf.copy()

        #make d be the same columns and index as df 
        if self.additional_dfs:
            self.additional_dfs_fixed = lmap(lambda d:  d.reindex(index=df.index, columns=df.columns), self.additional_dfs)

        return arr, df, self.used_type, fulldf

    def get_panel(self, unitetyp):
        unitetypeff = unitetyp
        if self.params.adjust_to_currency and self.params.currency_to_adjust:
            if self.params.currency_to_adjust != config.Symbols.BASECUR:
                df = self.readjust_for_currency(self.params.currency_to_adjust)
            else:
                df = self._eng.input_processor.adjusted_panel

        elif self.params.adjusted_for_base_cur:
            df = self._eng.input_processor.adjusted_panel
        else:
            df = self._eng.input_processor.reg_panel
        return df, unitetypeff



    def get_df_by_type(self, div, unitetyp):

        df, unitetypeff = self.get_panel(unitetyp)



        if (unitetyp & ~UniteType.ADDTOTALS == 0 )  and (div & (Types.PROFIT | Types.RELPROFIT | Types.TOTPROFIT | Types.VALUE)):
            additionaldfs = [ df['holding_by_stock'], df['alldates'] ]
        else:
            additionaldfs = None

        if div & Types.PROFIT:
            df = df['unrel_profit']
            # use_ext = False
        elif div & Types.RELPROFIT:
            df = df['rel_profit_by_stock']
            # use_ext = False
        # elif div & Types.PRICE:
        #     df = df['alldates']
        #     df=df.fillna(method='ffill', axis=1) #understand more before?
        elif div & Types.TOTPROFIT:
            df = df['tot_profit_by_stock']
        elif div & Types.VALUE:
            df = df['value']
            # use_ext = False
        elif div & Types.PERATIO:
            if not 'peratio' in df:
                raise NoDataException()
            df = df['peratio']
        elif div & Types.PRICESELLS:
            if not 'pricesells' in df:
                raise NoDataException()
            df = df['pricesells']
        elif div & Types.THEORTICAL_PROFIT:
            df = df['tot_profit_by_stock']
        else:  # logging.debug(('default!!')) #price
            df = df['alldates']
            df = df.fillna(method='ffill', axis=0)  # understand more before?
            if (unitetyp & UniteType.ADDPROT) and (unitetyp & ~UniteType.ADDTOTALS == 0) and (
                    div & Types.PRECDIFF == 0):  # (div& ~Types.COMPARE) and
                unitetypeff = unitetypeff & ~UniteType.ADDPROT
        if df.isnull().all(axis=None):
            raise NoDataException()

        return df.copy(), unitetypeff , additionaldfs

    def unite_groups(self, df):
        def filt(x, df):
            if not (x < set(df.columns)):
                logging.debug(('not enough stocks, not complete'))
                print(x - set(df.columns))
            return list(x.intersection(set(df.columns)))

        items = [(g, self._eng.Groups[g]) for g in self.params.groups]
        if (self.used_unitetype & ~UniteType.ADDTOTALS):  # Non trivial unite. groups
            reqsym = self._eng.required_syms(want_unite_symbols=True, only_unite=True).intersection(set(df.columns))
            if len(reqsym) > 0:
                ndf = df.loc[:, reqsym]
            else:
                ndf = pandas.DataFrame(index=df.index, )
        else:  # just add total
            ndf = df

        if self.used_unitetype & UniteType.ADDTOTALS:
            if self.used_unitetype & UniteType.ADDPROT:
                x = set(self._eng.input_processor.get_portfolio_stocks())
                items += [('Portfolio', filt(x, df))]
            else:  # add TOTAL
                x = set(self._eng.required_syms(True))
                items += [('All', filt(x, df))]

        for gr, stocks in items:
            try:
                arr = np.array(df[stocks]).transpose()
            except KeyError:
                logging.error('none of the values here')
                continue
            incomplete = (arr.shape[0] != len(stocks))
            if incomplete:
                logging.debug(('incomplete unite'))
            if len(arr)==0:
                return ndf,[]
            if self.used_unitetype & UniteType.SUM or gr in ['All', 'Portfolio']:

                ndf.loc[:, gr] = numpy.nansum(arr, axis=0)

            elif self.used_unitetype & UniteType.AVG:
                ndf.loc[:, gr] = numpy.nanmean(arr, axis=0)

        return ndf, [x[0] for x in items]

    def cols_by_selection(self, data):
        cols = set([x for x in data])
        selected = self._eng.required_syms(True).union(
            set(['All', 'Portfolio']))  # always include All if there is all..
        withoutext = self._eng.required_syms(False).union(set(['All', 'Portfolio']))

        return cols.intersection(selected), cols.intersection(withoutext)

    def generate_data(self):
        # self.params.use_ext=True #Will be changed by func

        self.get_data_by_type(self.params.type, self.params.compare_with)
        self.cols = self.df.columns
        if self.df.isnull().all(axis=None):
            raise NoDataException("Dataframe is empty")

        b = self.update_ranges()

        self.filter_ranges(b)
        self.finalcols=self.df.columns
        self.df_before_act = self.df_before_act [ self.df.columns]

        def conv_index(df):
            df.rename({y: matplotlib.dates.num2date(y) for y in df.index}, axis=0, inplace=1)  # problematicline
        conv_index(self.df)
        conv_index(self.df_before_act)


    def filter_ranges(self,  b):
        self.params.ignore_minmax = self.params.ignore_minmax or b
        mainlst = list(x for x in zip(self.Marr, self.min_arr, self.df.columns) if x[2] in self.colswithoutext)
        mainlst = sorted(mainlst, key=lambda x: x[0],
                         reverse=(self.params.limit_by == LimitType.MIN))
        condrange = lambda min, max: (min >= self.params.valuerange[0] and max <= self.params.valuerange[1])
        condmin = lambda min, max: (min >= self.params.valuerange[0] and min <= self.params.valuerange[1])
        condmax = lambda min, max: (max >= self.params.valuerange[0] and max <= self.params.valuerange[1])
        conddic = {LimitType.MIN: condmin, LimitType.MAX: condmax, LimitType.RANGE: condrange}
        cond = conddic[self.params.limit_by]
        sordlist = [stock for (max, min, stock) in mainlst if cond(min, max) or (self.params.ignore_minmax)]

        if not self.params.ignore_minmax:
            rang = (self.params.numrange[0], self.params.numrange[1])
        else:
            rang = (None, None)
        sordlist = sordlist[rang[0]:rang[1]]
        restofcols = set(self.df.columns) - set(self.colswithoutext)

        self.df = self.df[sorted(list(restofcols)) + sordlist]  # rearrange columns by max, and include rest

    def update_ranges(self):
        upd1 = self.tmp_colswithoutext != self.colswithoutext
        if upd1:
            self.colswithoutext = self.tmp_colswithoutext
            self._eng.namesChanged.emit(len(self.colswithoutext))

        M = max(list(self.df.max(numeric_only=True)))
        m = min(list(self.df.min(numeric_only=True)))
        diff = self.maxValue != M or self.minValue != m
        self.minValue, self.maxValue = m, M
        if diff:
            self._eng.minMaxChanged.emit((self.minValue, self.maxValue))
        return upd1 or diff

    def fill_same_currency(self,ncurrency,df: pandas.DataFrame):
        '''
        For example if we are in ILS and already another stock is ILS .
        '''
        def retk():
            for k in self._inp.symbol_info:
                if ( self._inp._data.get_currency_for_sym(k, True) == ncurrency or self._inp._data.get_currency_for_sym(k, False) == ncurrency):
                    yield k
        s=set(retk())
        for l in df.columns:
            if l[1] in s and l in self._inp._reg_panel.columns:
                df[l]= self._inp._reg_panel[l].copy()
        return df


    def key_maker(self,ncurrency):
        import random 
        if self.params.is_forced:
            return random.randint(0,100000)
        return (ncurrency, self.params.fromdate, self.params.todate)

    #TODO: use cached with smart key based on params
    @cached(custom_key_maker=key_maker,ttl=300)
    def readjust_for_currency(self, ncurrency):
        '''
        Adapt to a new home currency
        '''

        currency_hist = self._inp.get_currency_hist(ncurrency, self.params.fromdate,
                                                    self.params.todate)  # should be fine, the range
        simplified = (currency_hist['Open'] + currency_hist['Close']) / 2
        rate = self._inp.get_relevant_currency(ncurrency)
        if rate is None:
            logging.error(("cant adjust"))
            return
        newdf = self._inp.adjusted_panel.copy()  # adjusted_panel is already at base currency.
        for x in SymbolsInterface.TOADJUST:
            newdf[x] = newdf[x].mul(1 / rate)
        simplified = pandas.DataFrame(simplified, columns=['data'])
        simplified = simplified.set_index(matplotlib.dates.date2num(list(simplified.index)))
        oldind = min(simplified.index)
        oldnindex=min(newdf.index)
        oldmaxind= max(simplified.index)
        oldnmaxind=max(newdf.index)
        missingvalues = set(list(newdf.index)) - set(list(simplified.index))
        logging.debug((log_conv('missing in readjust', len(missingvalues))))

        simplified = simplified.reindex(newdf.index, method='pad')#padding just in between values

        if oldnindex<oldind:
            simplified.loc[oldnindex:oldind]=numpy.nan
        if oldnmaxind>oldmaxind:
            simplified.loc[oldmaxind:oldnmaxind] = numpy.nan



        for y in SymbolsInterface.TOADJUSTLONG:
            newdf[y] = newdf[y].mul(simplified['data'], axis=0)

        newdf = newdf[[(c, d) for (c, d) in self._inp.reg_panel.columns if c not in ['tot_profit_by_stock']]]
        t = newdf['rel_profit_by_stock'] + newdf['unrel_profit']
        t.columns = pandas.MultiIndex.from_product([['tot_profit_by_stock'], list(t.columns)],
                                                   names=['Name', 'Symbols'])
        newdf = pandas.concat([newdf, t], axis=1)
        return self.fill_same_currency(ncurrency,newdf)

    def serialize_me(self, filepath=config.File.SERIALIZEDFILE):
        logging.debug((f'writing serialized file to {config.File.SERIALIZEDFILE}'))
        with open(filepath, 'wb') as f:
            import pickle
            pickle.dump(self.serialized_data(), f)

    def serialized_data(self):
        return Serialized(self.orig_df, self.bef_rem_data, self.after_filter_data, self.act, self.params,
                          self._eng.Groups)

    def verify_conditions(self):
        return (self.params.fromdate is None or self.params.todate is None or self.params.fromdate < self.params.todate -datetime.timedelta(days=1) ) \
               and (self.params.use_groups and len(self.params.groups) > 0) or \
               (not self.params.use_groups and \
                len(self.params.selected_stocks) + (len(self.params.ext) if self.params.use_ext else 0) > 0)
