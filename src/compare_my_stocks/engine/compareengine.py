import logging
import threading

from config import config
from common.common import NoDataException, MySignal, Types, UniteType, InputSourceType
from common.simpleexceptioncontext import simple_exception_handling
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
            input_type =config.Input.INPUTSOURCE
            if input_type is None:
                return None
            if input_type == InputSourceType.IB:
                return get_ib_source()  # IBSource()
            elif input_type == InputSourceType.InvestPy:
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
        #the want it all is in the case of populating dict
        used_type = self.used_type if self.used_type is not None  else self.params.type
        used_unitetype= self.used_unitetype if self.used_unitetype is not None  else self.params.unite_by_group
        selected = set()
        if want_unite_symbols and (used_type & Types.COMPARE and self.params.compare_with): #notice that based on params type and not real type
            selected.update(set([self.params.compare_with]))


        if want_portfolio_if_needed and (self.params.unite_by_group & UniteType.ADDPROT):
            selected=set(self.transaction_handler.get_portfolio_stocks())

        if self.to_use_ext and include_ext:
            selected.update(set(self.params.ext))

        if (used_unitetype & ~UniteType.ADDTOTALS) and want_unite_symbols:
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
        #Any reason it is here?
        self.used_unitetype = self.params.unite_by_group
        requried_syms = self.required_syms(True, True)

        if self._inp.usable_symbols and (not (set(requried_syms) <= self._inp.usable_symbols)):
            symbols_needed = set(requried_syms) - self._inp.usable_symbols - self._inp._bad_symbols - set(
                config.Symbols.IGNORED_SYMBOLS) #TODO::make bad symbols property

            if len(symbols_needed) > 0:
                reprocess = 1
                logging.debug((f'should add stocks {symbols_needed}'))
            else:
                reprocess = 0
        else:
            symbols_needed = set()  # process all...
        adjust_date = False
        if reprocess:
            self._inp.process(symbols_needed)
            adjust_date = True
        if hasattr(self.params,'adjust_date'):
            adjust_date = adjust_date or  self.params.adjust_date
        else:
            self.params.adjust_date=0
        with self._datagenlock:
            res= self.call_data_generator()
            if res==2:
                adjust_date = True



        if res:
            df = self._datagen.df
            type = self._datagen.type
            before_act = self._datagen.df_before_act
            self.call_graph_generator(df, just_upd,type,before_act , adjust_date= adjust_date , additional_df=self._datagen.additional_dfs_fixed) 

    @simple_exception_handling(err_description="Exception in generation")
    def call_data_generator(self,auto_reprocess=True):
        b=0
        for tries in range(2):
            if not self._datagen.verify_conditions():
                self.statusChanges.emit('Graph Invalid! Check parameters')
                return False
            try:
                self._datagen.generate_data()
                return 1+b
            except NoDataException:
                if auto_reprocess:
                    logging.debug("No data first try. reprocessing")
                    self._inp.process(self.required_syms(True, True))
                    b=1
                    continue
                else:
                    self.statusChanges.emit('No Data For Graph!')
                    logging.debug(('no data'))
                    return False
            except Exception as e:
                self.statusChanges.emit(f'Exception in generation: {e}')
                raise

    def call_graph_generator(self, df, just_upd, type,orig_data,adjust_date=False,additional_df=None):
        if df.empty:
            self.statusChanges.emit(f'No Data For Graph!')
            return
        def upd(msg,err=False):
            self.statusChanges.emit(msg)
            self._inp.failed_to_get_new_data=None #reset it
            if err:
                logging.error(msg)
            else:
                logging.info(msg)

        plot_data = {}
        if ((Types.PRECENTAGE | Types.DIFF | Types.COMPARE)  & type) == 0 and self.params.unite_by_group & (UniteType.SUM | UniteType.AVG)==0:
            try:
                plot_data= self._tr.get_data_for_graph(list(df.columns),df.index[0],df.index[-1])
            except:
                logging.error("failed to get transaction data for graph")




        try:
            self._generator.gen_actual_graph(list(df.columns), df, self.params.isline, self.params.starthidden,
                                             just_upd, type,orig_data,adjust_date=adjust_date,plot_data=plot_data,additional_df=additional_df)
            if self._inp.failed_to_get_new_data:
                upd(f"Generated Graph with old data  (  Query failed :() ")
            else:
                upd("Generated Graph :)")
            self.finishedGeneration.emit(1)
        except TypeError as e:
            upd(f"failed generating graph {e}",err=True)
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

    def process(self, *args,**kwargs):
        return self._inp.process(*args,**kwargs)

    def get_portfolio_stocks(self):
        return self.transaction_handler.get_portfolio_stocks()

