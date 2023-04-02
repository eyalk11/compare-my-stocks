import logging
import threading

from config import config
from common.common import NoDataException, MySignal, simple_exception_handling, Types, UniteType, InputSourceType
from engine.compareengineinterface import CompareEngineInterface
from engine.symbolshandler import SymbolsHandler
from input.ibsource import get_ib_source
from input.inputsource import InputSourceInterface
from input.investpysource import InvestPySource

from processing.datagenerator import DataGenerator
from graph.graphgenerator import GraphGenerator
from input.inputprocessor import InputProcessor
from engine.parameters import Parameters
from transactions.transactionhandlermanager import TransactionHandlerManager


class InternalCompareEngine(SymbolsHandler,CompareEngineInterface):
    statusChanges = MySignal(str)
    finishedGeneration = MySignal(int)
    minMaxChanged = MySignal(tuple)
    namesChanged = MySignal(int)

    @staticmethod
    @simple_exception_handling(err_description='Input source initialization failed. ',never_throw=True)
    def get_input_source(input_type  : InputSourceType = None):
        if input_type is None:
            input_type =config.INPUTSOURCE
            if input_type == InputSourceType.IB:
                return get_ib_source()  # IBSource()
            else:
                return InvestPySource()


    def __init__(self, axes=None):
        SymbolsHandler.__init__(self)
        input_source=  self.get_input_source()

        self._tr = TransactionHandlerManager(None)
        self._inp = InputProcessor(self, self._tr,input_source)
        self._tr._inp = self._inp  # double redirection.

        self._datagen: DataGenerator = DataGenerator(self)
        self._generator: GraphGenerator = GraphGenerator(self, axes)

        self._annotation = []
        self._cache_date = None

        self.read_groups_from_file()
        self._datagenlock = threading.Lock()

    def  required_syms(self, include_ext=True, want_portfolio_if_needed=False, want_unite_symbols=False,only_unite=False):
        if not self._datagen.data_generated:
            logging.debug("didnt generate")
        #the want it all is in the case of populating dict
        selected = set()
        if want_unite_symbols and (self.used_type & Types.COMPARE and self.params.compare_with): #notice that based on params type and not real type
            selected.update(set([self.params.compare_with]))


        if want_portfolio_if_needed and (self.params.unite_by_group & UniteType.ADDPROT):
            selected=set(self.transaction_handler.get_portfolio_stocks())

        if self.to_use_ext and include_ext:
            selected.update(set(self.params.ext))

        if (self.used_unitetype & ~UniteType.ADDTOTALS) and want_unite_symbols:
            if only_unite: #it is a bit of cheating but we don't need to specify require data symbols in that case
                return selected
        if  self.params.use_groups:
            return selected.union(self.get_options_from_groups(self.params.groups))
        else:
            return selected.union(self.params.selected_stocks)

    def gen_graph(self, params: Parameters, just_upd=0, reprocess=1):
        if just_upd and self.params:
            self.params.update_from(params)
        else:
            self.params = params

        self.params._baseclass = self

        self.to_use_ext = self.params.use_ext
        self.used_unitetype = self.params.unite_by_group
        requried_syms = self.required_syms(True, True)

        if self._inp.usable_symbols and (not (set(requried_syms) <= self._inp.usable_symbols)):
            symbols_needed = set(requried_syms) - self._inp.usable_symbols - self._inp._bad_symbols - set(
                config.IGNORED_SYMBOLS) #TODO::make bad symbols property

            if len(symbols_needed) > 0:
                reprocess = 1
                logging.debug((f'should add stocks {symbols_needed}'))
            else:
                reprocess = 0
        else:
            symbols_needed = set()  # process all...

        if reprocess:
            self._inp.process(symbols_needed)
            self.adjust_date = True


        with self._datagenlock:
            res= self.call_data_generator()
            df= self._datagen.df
            type=self._datagen.type
            before_act =self._datagen.df_before_act

        if res:
            self.call_graph_generator(df, just_upd,type,before_act )

    @simple_exception_handling(err_description="Exception in generation")
    def call_data_generator(self):
        if not self._datagen.verify_conditions():
            self.statusChanges.emit(f'Graph Invalid!')
            return False
        try:
            self._datagen.generate_data()
            return True
        except NoDataException:
            self.statusChanges.emit(f'No Data For Graph!')
            logging.debug(('no data'))
            return False
        except Exception as e:
            self.statusChanges.emit(f'Exception in generation: {e}')
            raise

    def call_graph_generator(self, df, just_upd, type,orig_data):
        try:
            self._generator.gen_actual_graph(list(df.columns), df, self.params.isline, self.params.starthidden,
                                             just_upd, type,orig_data)
            self.statusChanges.emit("Generated Graph :)")
            logging.info("Generated graph")
            self.finishedGeneration.emit(1)
        except TypeError as e:
            e = e
            logging.error("failed generating graph ")
            self.statusChanges.emit(f"failed generating graph {e}")
            raise

    # makes the entire graph from the default attributes.
    def update_graph(self, params: Parameters = Parameters()):
        reprocess = 1 if (not self.input_processor._alldates) else 0

        params.increase_fig = False
        self.gen_graph(params, just_upd=1, reprocess=reprocess)


class CompareEngine(InternalCompareEngine):
    '''
    Here we just add the proxy methods.
    '''

    def serialized_data(self):
        return self._datagen.serialized_data()

    @property
    def adjust_date(self):
        return self._generator.adjust_date

    @adjust_date.setter
    def adjust_date(self, value):
        self._generator.adjust_date = value

    @property
    def input_processor(self):
        return self._inp

    @property
    def transaction_handler(self):
        return self._tr

    @property
    def colswithoutext(self):
        return self._datagen.colswithoutext

    @property
    def minValue(self):
        return self._datagen.minValue

    @property
    def maxValue(self):
        return self._datagen.maxValue

    @property
    def maxdate(self):
        if self._inp:
            return self._inp.maxdate
        else:
            return None

    @property
    def mindate(self):
        if self._inp:
            return self._inp.mindate
        else:
            return None

    @property
    def to_use_ext(self):
        """doc"""
        return self._datagen.to_use_ext

    @to_use_ext.setter
    def to_use_ext(self, value):
        self._datagen.to_use_ext = value

    @property
    def used_type(self):
        return self._datagen.used_type
    @property
    def used_unitetype(self):
        """doc"""
        return self._datagen.used_unitetype

    @used_unitetype.setter
    def used_unitetype(self, value):
        self._datagen.used_unitetype = value

    @property
    def inputsource(self) -> InputSourceInterface:
        return self._inp.inputsource

    @property
    def usable_symbols(self):
        return self._inp.usable_symbols

    @property
    def visible_columns(self):
        return self._generator.get_visible_cols()
    @property
    def final_columns(self):
        return self._datagen.finalcols

    def show_hide(self,val):
        return self._generator.show_hide(val)

    def process(self,*args,**kwargs):
        return self._inp.process(*args,**kwargs)

    def get_portfolio_stocks(self):
        return self.transaction_handler.get_portfolio_stocks()

