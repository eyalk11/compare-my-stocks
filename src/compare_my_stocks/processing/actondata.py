import logging
import math

import numpy as np

from common.common import Types, get_first_where_all_are_good, dictnfilt, NoDataException
from config import config

from input.inputdata import InputData

class ActOnData:
    def __init__(self, arr, df, type, fulldf, compare_with, inputData: InputData):
        self.arr=arr
        self.df=df
        self.type=type
        self.fulldf=fulldf
        self._ds=inputData
        self.compare_with=compare_with
        self.transpose_arr = self.arr.transpose()
    def __getstate__(self):
        return dictnfilt(self.__dict__,set(['_ds']))

    def handle_operation(self):
        if config.DEBUG:
            self.org_arr=self.arr.copy()

        if self.type & Types.PRECENTAGE:
            newarr = (self.transpose_arr / self.refarr - (1 if self.type & Types.RELTOSTART | Types.RELTOMIN else 0)) * 100

        elif self.type & Types.DIFF:
            newarr = self.transpose_arr - self.refarr
        else:  # if self.type & Types.ABS == Types.ABS:
            newarr = self.transpose_arr
        if config.DEBUG:
            self.refarr=self.refarr.copy()
            #self.newarr=newarr.copy()
        # we want to transpose the array anyway to get it fit to self.df...
        return  newarr

    def get_ref_array(self,arr):
        if len(arr.shape)==1:
            if self.type & Types.RELTOMAX:
                refarr = np.nanmax(arr)
            elif self.type & Types.RELTOMIN:
                refarr = np.nanmin(arr)

            elif self.type & Types.RELTOEND:
                refarr = arr[-1]
            else:  # if self.type & Types.RELTOSTART:TODO:: the rel things should be another type like unite.. some messy code...
                refarr = arr[ 0]
        else:
            if arr.shape[1]==0:
                logging.debug(('errarr'))
                raise NoDataException()
            if self.type & Types.RELTOMAX:
                refarr = np.nanmax(arr,axis=1)
            elif self.type & Types.RELTOMIN:
                refarr = np.nanmin(arr, axis=1)

            elif self.type & Types.RELTOEND:
                refarr = arr[:, -1]
            else:  # if self.type & Types.RELTOSTART:TODO:: the rel things should be another type like unite.. some messy code...
                refarr = arr[:, 0]
        return refarr

    def handle_compare(self):
        ign=False

        compit_arr = np.array(self.fulldf[self.compare_with])
        compit = np.vstack([compit_arr] * len(self.df.columns))

        compit_initial = self.get_ref_array(compit_arr)  # at f=0 - ref value


        transpose_compit = compit.transpose()

        if self.type & (Types.PRECENTAGE | Types.DIFF) == (Types.PRECENTAGE | Types.DIFF):
            newarr = ((self.transpose_arr / self.refarr - transpose_compit / compit_initial)) * 100
            ign = True

        elif self.type & Types.PRECENTAGE:  # by what factor was it better...
            newarr = ((self.transpose_arr / self.refarr) / (transpose_compit / compit_initial) - 1) * 100
            ign=True
        else:
            newarr = self.transpose_arr - transpose_compit

        self.arr, self.transpose_arr =  newarr.transpose(),  newarr
        return ign

    def calc_theoritical_profit(self):
        firstnotNan = lambda x: next((l for l in x.values() if not math.isnan(l)))
        firstKeynotNan = lambda x: next((k for k,l in x.items() if not math.isnan(l)))
        holdDF= self._ds.holding_by_stockDF[[x for x in self.df] + [self.compare_with]]
        holdArr= np.array(holdDF).transpose()
        ind= get_first_where_all_are_good(holdArr)

        holdArr= holdArr.iloc[ind:] #we assume avg cost is valid if hold is
        minkey = firstKeynotNan(self._ds.alldates[self.compare_with])
        holdArr=holdArr[(holdArr.index >= minkey) ]
        self.df = self.df[(self.df.index >= max(minkey,holdArr.index[0]) ) ]

        for st in self.df: #if we query on the df. we must be after hold and that is enough...
            # if we hold the same value as we hold for QQQ what is the difference
            initialHold = firstnotNan(self._ds.holding_by_stock[st])
            intialCost = firstnotNan(self._ds.avg_cost_by_stock[st])
            loc = firstKeynotNan(self._ds.holding_by_stock[st])
            intialHoldComp = (initialHold * intialCost) / self._ds.alldates[self.compare_with][loc]
            intialCostComp = self._ds.alldates[self.compare_with][loc]
            holdcomp = lambda f: intialHoldComp * self._ds.holding_by_stock[st][f] / initialHold
            costcomp = lambda f: intialCostComp * self._ds.avg_cost_by_stock[st][f] / intialCost

            yield [holdcomp(f) * costcomp(f) for f in self._ds.curflist]
                # compit_arr ={f:} #from here , either precentage or diff

    def fixinf(self,arr):
        arr[np.isinf(arr)] = np.nan
        return arr
        # self.arr[np.isinf(self.arr)]=np.nan

    def do(self):

        self.refarr = self.get_ref_array(self.arr)

        if self.type & (Types.COMPARE | Types.THEORTICAL_PROFIT)==(Types.COMPARE | Types.THEORTICAL_PROFIT):
            self.df = self.calc_theoritical_profit()


        ign=False

        if self.type & Types.COMPARE:
            ign = self.handle_compare()



        if ign:
            self.newarr = self.fixinf(self.transpose_arr)
        else:
            self.newarr = self.fixinf(self.handle_operation())

        self.df.loc[:, self.df.columns] =self.newarr

        self.Marr = np.nanmax(self.newarr, axis=0)
        self.min_arr = np.nanmin(self.newarr, axis=0)
