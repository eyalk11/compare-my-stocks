import matplotlib
import numpy
import numpy as np
import pandas

from common.common import Types, UniteType, NoDataException, get_first_where_all_are_good
#from compareengine import CompareEngine
from processing.actondata import ActOnData
from input.inputdata import InputData
from engine.parameters import HasParamsAndGroups, ParameterError


class DataGenerator(HasParamsAndGroups, InputData):


    def get_data_by_type(self, type= Types.RELTOMAX, compare_with=None):
        arr, df, type, fulldf = self.generate_initial_data(compare_with, type)
        act= ActOnData(arr, df, type, fulldf,compare_with,self)
        act.do()

        return  act.df,act.Marr,act.type

    def generate_initial_data(self, compare_with, div):
        fromdateNum = matplotlib.dates.date2num(self.params.fromdate) if self.params.fromdate else 0
        todateNum = matplotlib.dates.date2num(self.params.todate) if self.params.todate else float('inf')
        dic = self.get_dict_by_type(div)
        df = pandas.DataFrame.from_dict(dic)
        if (self.params.unite_by_group & ~UniteType.NONE):
            df = self.unite_groups(df)
        df = df[(df.index >= fromdateNum) * (df.index <= todateNum)]
        compit_arr = None
        if div & Types.COMPARE:
            if not compare_with in df:
                print('to bad, no comp')
                div = div & ~Types.COMPARE

                # ind=first_index_of(compit_arr,np.isnan)
                # df=df.iloc[ind:]
        if not (self.params.unite_by_group & ~(UniteType.ADDTOTAL)):  # in unite, the compare_with is already there
            cols = self.cols_by_selection(df, div)
            if div & Types.COMPARE:
                fulldf = df[list(cols.union(set([compare_with])))]
            else:
                fulldf = df
        else:
            fulldf = df
            cols=set(df.columns)
            ##else we need everything...
        arr = np.array(fulldf).transpose()  # will just work with arr
        fulldf = fulldf.drop(
            df.index[(np.all(np.isnan(arr), axis=0))])  # to check drop dates in which all stocks are none.
        df = fulldf[list(cols - set([compare_with]))]
        arr = np.array(df).transpose()  # will just work with arr

        if len(arr)==0:
            raise NoDataException("arr is empty")

        if div & (Types.COMPARE |Types.PRECENTAGE | Types.DIFF):
            fullarr= np.array(fulldf).transpose()
            df = df.iloc[get_first_where_all_are_good(fullarr):]
            arr = np.array(df).transpose()

        self.org_data=fulldf.copy()
        return arr, df, div, fulldf

    def get_dict_by_type(self, div):
        if div & Types.PROFIT:
            dic = self.unrel_profit
            self.params.use_ext = False
        elif div & Types.RELPROFIT:
            dic = self.rel_profit_by_stock
            self.params.use_ext = False
        elif div & Types.PRICE:
            dic = self.alldates
        elif div & Types.TOTPROFIT:
            dic = self.tot_profit_by_stock
        elif div & Types.VALUE:
            dic = self.value
            self.params.use_ext = False
        elif div & Types.THEORTICAL_PROFIT:
            dic = self.tot_profit_by_stock
        else:
            dic = self.alldates
        return dic

    def unite_groups(self, df):

        items = [(g, self.Groups[g]) for g in self.params.groups]
        if (self.params.unite_by_group & ~UniteType.ADDTOTAL):
            ndf=pandas.DataFrame(index=df.index)

        else:
            ndf=df

        if self.params.unite_by_group & UniteType.ADDTOTAL:
            items += [('All', list(df.columns))]




        for gr, stocks in items:
            try:
                arr = np.array(df[stocks]).transpose()
            except KeyError:
                print('none of the values here')
                continue
            incomplete= (arr.shape[0]!=len(stocks))
            if incomplete:
                print('incomplete unite')
            #curdat = {st:{f: dic[stocks[st]][self._curflist[f]]}  for st in range(len(stocks)) for f in range(len(self._curflist))} #should have default args
            #A=numpy.array(curdat)
            # = n[~numpy.isnan(n)]

            if self.params.unite_by_group & UniteType.SUM or gr=='All':
                ndf.loc[:, gr] = numpy.sum(arr, axis=0)
                #df.append({'gr':  },ignore_index=True)
            elif self.params.unite_by_group & UniteType.AVG:
                ndf.loc[:, gr] = numpy.nanmean(arr, axis=0 )

        return ndf

    def cols_by_selection(self,  data,div):
        cols = set([x for x in data])
        selected=set(['All']) #always include All if there is all..


        if self.params.use_ext:
            selected.update(set(self.params.ext))
        try:
            if self.params.use_groups:
                if self.params.groups:

                    for g in self.params.groups:
                        selected.update((set(self.Groups[g])))


            else:
                selected.update(set(self.params.selected_stocks))
        except KeyError:
            raise ParameterError("groups")



        return cols.intersection(selected)

    def generate_data(self):
        #self.params.use_ext=True #Will be changed by func

        df, Marr,div= self.get_data_by_type(self.params.type, self.params.compare_with)

        sordlist = [stock for (max, stock) in sorted(list(zip(Marr, df)), key=lambda x: x[0], reverse=True) if
                    max >= self.params.mincrit]
        df = df[sordlist[:self.params.maxnum]]  # rearrange columns by max
        df.rename({y: matplotlib.dates.num2date(y) for y in df.index},axis=0,inplace=1)

        return df,div