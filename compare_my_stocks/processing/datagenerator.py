import matplotlib
import numpy
import numpy as np
import pandas




from common.common import Types, UniteType, NoDataException, get_first_where_all_are_good, MySignal, Serialized
#from compareengine import CompareEngine
from config import config
from processing.actondata import ActOnData
from input.inputdata import InputData

from engine.symbolsinterface import SymbolsInterface

class DataGenerator(SymbolsInterface, InputData):
    minMaxChanged=MySignal(tuple)
    namesChanged = MySignal(int)
    statusChanges= MySignal(str)
    def __init__(self):
        #DataGenerator.minMaxChanged.initemit()
        self.colswithoutext=[]
        self.tmp_colswithoutext=[]
        self.after_filter_data=None
        self.minValue=None
        self.maxValue=None
        self.cols=None
        self.act=None

    def get_data_by_type(self, type= Types.RELTOMAX, compare_with=None):
        arr, df, type, fulldf = self.generate_initial_data(compare_with, type)
        act= ActOnData(arr, df, type, fulldf,compare_with,self)
        self.act=act
        act.do()

        return  act.df,act.Marr,act.min_arr,act.type

    def generate_initial_data(self, compare_with, type):
        fromdateNum = matplotlib.dates.date2num(self.params.fromdate) if self.params.fromdate else 0
        todateNum = matplotlib.dates.date2num(self.params.todate) if self.params.todate else float('inf')

        df,self.used_unitetype = self.get_df_by_type(type,self.params.unite_by_group)
        self.orig_df = df
        self.used_type=type
        #self.to_use_ext = use_ext and self.params.use_ext
        self.to_use_ext =self.params.use_ext
        if (self.used_unitetype & ~UniteType.NONE):
            df , colswithoutext = self.unite_groups(df) #in case really unite groups, colswithoutext is correct

        df = df[(df.index >= fromdateNum) * (df.index <= todateNum)]

        if self.used_type & Types.COMPARE:
            if not compare_with in df:
                print('to bad, no comp')
                self.used_type = self.used_type & ~Types.COMPARE

                # ind=first_index_of(compit_arr,np.isnan)
                # df=df.iloc[ind:]
        comp_set = (set([compare_with]) if self.used_type & Types.COMPARE else set())

        if not (self.params.unite_by_group & ~(UniteType.ADDTOTALS)):  # in unite, the compare_with is already there.
            # If the  unite is non-trivial, then colswithoutext already returned
            cols,colswithoutext = self.cols_by_selection(df)
            #if self.used_type & Types.COMPARE:
            fulldf = df[sorted(list(cols.union(comp_set)))]
        else: #colswithoutext non-trivial
            fulldf = df
            cols=set(df.columns)

            ##else we need everything...
        self.bef_rem_data = fulldf.copy()
        arr = np.array(fulldf).transpose()  # will just work with arr
        fulldf = fulldf.drop(list(
            df.index[list((np.all(np.isnan(arr), axis=0)))]))  # to check drop dates in which all stocks are none.

        if self.used_type & (Types.COMPARE | Types.PRECENTAGE | Types.DIFF):
            fullarr = np.array(fulldf).transpose() #again...
            fulldf = fulldf.iloc[get_first_where_all_are_good(fullarr, self.used_type & Types.PRECENTAGE):]
            if self.used_type & (Types.RELTOEND):
                fulldf = fulldf.iloc[:get_first_where_all_are_good(fullarr, self.used_type & Types.PRECENTAGE, last=1)]

        df = fulldf[sorted(list(cols - comp_set))]
        arr = np.array(df).transpose()  # will just work with arr

        if len(arr)==0:
            raise NoDataException("arr is empty")

        self.tmp_colswithoutext=  set(colswithoutext).intersection(df.columns)
        self.after_filter_data=fulldf.copy()

        return arr, df, self.used_type, fulldf

    def get_df_by_type(self, div,unitetyp):

        unitetypeff=unitetyp
        if self.params.adjusted_for_base_cur:
            df=self.adjusted_panel
        else:
            df=self.reg_panel

        if self.params.adjust_to_currency and self.params.currency_to_adjust:
            if self.params.currency_to_adjust != config.BASECUR:
                df=self.readjust_for_currency(self.params.currency_to_adjust)

        if div & Types.PROFIT:
            df = df['unrel_profit']
            #use_ext = False
        elif div & Types.RELPROFIT:
            df = df['rel_profit_by_stock']
            #use_ext = False
        # elif div & Types.PRICE:
        #     df = df['alldates']
        #     df=df.fillna(method='ffill', axis=1) #understand more before?
        elif div & Types.TOTPROFIT:
            df = df['tot_profit_by_stock']
        elif div & Types.VALUE:
            df = df['value']
            #use_ext = False
        elif div & Types.PERATIO:
            if not 'peratio' in df:
                raise NoDataException()
            df=df['peratio']
        elif div & Types.PRICESELLS:
            if not 'pricesells' in df:
                raise NoDataException()
            df = df['pricesells']
        elif div & Types.THEORTICAL_PROFIT:
            df = df['tot_profit_by_stock']
        else:
            #print('default!!') #price
            df = df['alldates']
            df = df.fillna(method='ffill', axis=1)  # understand more before?
            if ( unitetyp & UniteType.ADDPROT) and (unitetyp & ~UniteType.ADDTOTALS ==0 )  and (div & Types.PRECDIFF ==  0): #(div& ~Types.COMPARE) and
                unitetypeff = unitetypeff & ~UniteType.ADDPROT
        if df.isnull().all(axis=None):
            raise NoDataException()
        return df.copy(),unitetypeff

    def unite_groups(self, df):
        def filt(x,df):
            if not (x <  set(df.columns)):
                print('not enough stocks, not complete')
                print (x- set(df.columns))
            return list(x.intersection(set(df.columns)))

        items = [(g, self.Groups[g]) for g in self.params.groups]
        if (self.used_unitetype & ~UniteType.ADDTOTALS): #Non trivial unite. groups
            reqsym= self.required_syms(data_symbols_for_unite=True).intersection(set(df.columns) )
            if len(reqsym )>0:
                ndf= df.loc[:, reqsym]
            else:
                ndf=pandas.DataFrame(index=df.index,)
        else: #just add total
            ndf=df


        if self.used_unitetype & UniteType.ADDTOTALS:
            if self.used_unitetype & UniteType.ADDPROT:
                x=set(self.get_portfolio_stocks())
                items += [('Portfolio', filt(x,df) )]
            else: #add TOTAL
                x=set(self.required_syms(True))
                items += [('All', filt(x,df))]




        for gr, stocks in items:
            try:
                arr = np.array(df[stocks]).transpose()
            except KeyError:
                print('none of the values here')
                continue
            incomplete= (arr.shape[0]!=len(stocks))
            if incomplete:
                print('incomplete unite')
            if self.used_unitetype & UniteType.SUM or gr in ['All','Portfolio']:

                ndf.loc[:, gr] = numpy.nansum(arr, axis=0)

            elif self.used_unitetype & UniteType.AVG:
                ndf.loc[:, gr] = numpy.nanmean(arr, axis=0 )

        return ndf ,[x[0] for x in items]



    def cols_by_selection(self,  data):
        cols = set([x for x in data])
        selected=self.required_syms(True).union(set(['All','Portfolio'])) #always include All if there is all..
        withoutext=self.required_syms(False).union(set(['All','Portfolio']))
        return cols.intersection(selected),cols.intersection(withoutext)

    def generate_data(self):
        #self.params.use_ext=True #Will be changed by func

        df, Marr ,min_arr, type= self.get_data_by_type(self.params.type, self.params.compare_with)

        self.cols = df.columns

        b=self.update_ranges(df)
        self.params.ignore_minmax= self.params.ignore_minmax or b

        mainlst= sorted(list(zip(Marr, min_arr, self.colswithoutext)), key=lambda x: x[0], reverse=True)


        sordlist = [stock for (max,min, stock) in mainlst  if
                    (min >= self.params.valuerange[0] and max<= self.params.valuerange[1]) or (self.params.ignore_minmax) ]
        restofcols= set(df.columns) - set(self.colswithoutext)
        if not self.params.ignore_minmax:
            rang =  (self.params.numrange[0],  self.params.numrange[1])
        else:
            rang=(None,None)

        df = df[sorted(list(restofcols))+ sordlist[rang[0]:rang[1]]  ]  # rearrange columns by max, and include rest
        df.rename({y: matplotlib.dates.num2date(y) for y in df.index},axis=0,inplace=1) #problematicline

        return df,type

    def update_ranges(self, df):
        upd1=self.tmp_colswithoutext!=self.colswithoutext
        if upd1:
            self.colswithoutext=self.tmp_colswithoutext
            self.namesChanged.emit(len(self.colswithoutext))

        M = max(list(df.max(numeric_only=True)))
        m = min(list(df.min(numeric_only=True)))
        diff = self.maxValue != M or self.minValue != m
        self.minValue, self.maxValue = m, M
        if diff:
            self.minMaxChanged.emit((self.minValue, self.maxValue))
        return upd1 or diff

    def readjust_for_currency(self,ncurrency):

        currency_hist= self.get_currency_hist(ncurrency,self.currencyrange[0],self.currencyrange[1]) #should be fine, the range
        simplified= (currency_hist['Open']+currency_hist['Close'])/2
        rate= self.get_relevant_currency(ncurrency)

        nn= self.adjusted_panel.copy() #adjusted_panel is already at base.
        for x in self.TOADJUST:
            nn[x]= nn[x].mul(1/rate)
        simplified =pandas.DataFrame(simplified,columns=['data'])
        simplified=simplified.set_index(matplotlib.dates.date2num(list(simplified.index)))
        missingvalues = set(list(nn.index)) - set(list(simplified.index))
        print('missing in readjust', len(missingvalues))
        simplified=simplified.reindex(nn.index,method='pad')


        for y in SymbolsInterface.TOADJUSTLONG:
            nn[y]=nn[y].mul(simplified['data'],axis=0)

        nn = nn[[(c, d) for (c, d) in self.reg_panel.columns if c not in ['tot_profit_by_stock']]]
        t = nn['rel_profit_by_stock'] + nn['unrel_profit']
        t.columns = pandas.MultiIndex.from_product([['tot_profit_by_stock'], list(t.columns)], names=['Name', 'Symbols'])
        nn = pandas.concat([nn, t], axis=1)
        return nn

    def serialize_me(self):
        with open(config.SERIALIZEDFILE,'wb') as f:
            import pickle
            pickle.dump(Serialized(self.orig_df,self.bef_rem_data, self.after_filter_data, self.act), f)
