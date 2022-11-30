import json

from common.dolongprocess import DoLongProcess
from config import config
from common.common import NoDataException, UniteType, Types
from engine.symbolsinterface import SymbolsInterface
from processing.datagenerator import DataGenerator
from graph.graphgenerator import GraphGenerator
from input.inputprocessor import InputProcessor
from engine.parameters import Parameters
from transactions.transactionhandlermanager import TransactionHandlerManager


class CompareEngine(GraphGenerator, InputProcessor, DataGenerator, SymbolsInterface):
    @property
    def params(self) -> Parameters:
        return self._params

    @params.setter
    def params(self,value : Parameters):
        self._params = value

    @property
    def Categories(self):
        return self._categories

    @property
    def cur_category(self) -> str:
        param=self.params
        if param:
            param= self.params.cur_category
        if param==None:
            return self._categories[0]
        return param

    @cur_category.setter
    def cur_category(self, value: str):
        if self.params:
            self.params.cur_category = value


    @property
    def Groups(self):
        return self._groups_by_cat[self.cur_category]

    def get_options_from_groups(self,ls):

        if not ls:
            return []
        s = set()
        for g in ls:
            if g not in self.Groups:
                raise Exception(f'{g} is not in Groups')
                #return []
            s = s.union(set(self.Groups[g]))
        if self.params.limit_to_portfolio:
            s=s.intersection(set(self.get_portfolio_stocks()))
        return list(s)



    def read_groups_from_file(self):
        try:
            jsongroups= json.load(open(config.JSONFILENAME,'rt'))
            self._groups_by_cat = jsongroups
            self._categories= list(self._groups_by_cat.keys())
            # if self.cur_category==None:
                # self.cur_category=self._categories[0]
        except:
            import traceback
            traceback.print_exc()
            logging.debug(('exception in  groups file')) #raise Exception("error reading groups"))

    def __init__(self,axes=None):
        super(CompareEngine, self).__init__(axes)
        tr= TransactionHandlerManager(self)
        InputProcessor.__init__(self,self,tr) #It is kind of lame as InputProcessor uses it as variable but it actually points to self. Whereas compareengine uses directly inputporcessor fields.
        DataGenerator.__init__(self)

        self._annotation=[]
        self._cache_date=None
        self.params=None


        #self._groups = config.GROUPS
        self._categories=None
        self._cur_category = None
        self._groups_by_cat = {}
        self.read_groups_from_file()



    def  required_syms(self, include_ext=True, want_it_all=False, data_symbols_for_unite=False): #the want it all is in the case of populating dict
        selected = set()
        if data_symbols_for_unite and (self.used_type & Types.COMPARE and self.params.compare_with): #notice that based on params type and not real type
            selected.update(set([self.params.compare_with]))


        if want_it_all and (self.params.unite_by_group & UniteType.ADDPROT):
            selected=set(self.get_portfolio_stocks())

        if self.to_use_ext and include_ext:
            selected.update(set(self.params.ext))
        if (self.used_unitetype & ~UniteType.ADDTOTALS) and data_symbols_for_unite:
            #logging.debug(('nontrivla'))
            return selected #it is a bit of cheating but we don't need to specify require data symbols in that case
        if  self.params.use_groups:
            return selected.union(self.get_options_from_groups(self.params.groups))
        else:
            return selected.union(self.params.selected_stocks)

        #t = inspect.getfullargspec(CompareEngine.gen_graph)  # generate all fields from paramters of gengraph
        #[self.__setattr__(a, d) for a, d in zip(t.args[1:], t.defaults)]

    def gen_graph(self, params: Parameters, just_upd=0, reprocess=1):
        if just_upd and self.params:
             self.params.update_from(params)
        else:
            self.params=params

        self.params._baseclass=self

        self.to_use_ext = self.params.use_ext
        self.used_unitetype = self.params.unite_by_group
        requried_syms = self.required_syms(True, True)
        if self._usable_symbols and (not (set(requried_syms) <=self._usable_symbols)):
            symbols_neeeded= set(requried_syms) - self._usable_symbols - self._bad_symbols  -set(config.IGNORED_SYMBOLS)

            if len(symbols_neeeded)>0:
                reprocess=1
                logging.debug((f'should add stocks {symbols_neeeded}'))
            else:
                reprocess=0
        else:
            symbols_neeeded=set() #process all...

        B = (1, 0.5)
        if reprocess:
            self.process(symbols_neeeded)
        try:
            self.df, type = self.generate_data()
        except NoDataException:
            self.statusChanges.emit(f'No Data For Graph!')
            logging.debug(('no data'))
            return
        except Exception as e:
            import traceback
            traceback.print_exc()
            e = e
            logging.debug(('exception in generating data'))
            self.statusChanges.emit(f'Exception in gen: {e}'  )
            if config.DEBUG:
                pass#raise
            return

        self.call_graph_generator(B, just_upd, type)

    def call_graph_generator(self, B, just_upd, type):
        try:
            self.gen_actual_graph(B, list(self.df.columns), self.df, self.params.isline, self.params.starthidden,
                                  just_upd, type)
            self.statusChanges.emit("Generated Graph :)")
            self.finishedGeneration.emit(1)
        except TypeError as e:
            e = e
            logging.debug(("failed generating graph "))
            self.statusChanges.emit(f"failed generating graph {e}")
            raise

    # makes the entire graph from the default attributes.
    def update_graph(self, params: Parameters = Parameters()):
        reprocess= 1 if  (not self._alldates) else 0

        params.increase_fig=False
        #t = inspect.getfullargspec(CompareEngine.gen_graph)
        #dd={x:self.__getattribute__(x) for x in t.args if x not in ['self','increase_fig','reprocess','just_upd' ] }
        self.gen_graph(params,just_upd=1,reprocess=reprocess )

