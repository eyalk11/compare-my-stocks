import json

from config import config
from common.common import NoDataException, UniteType, Types
from engine.symbolsinterface import SymbolsInterface
from processing.datagenerator import DataGenerator
from graph.graphgenerator import GraphGenerator
from input.inputprocessor import InputProcessor
from engine.parameters import Parameters


def params():
    doc = "The params property."

    def fget(self):
        return self._params

    def fset(self, value):
        self._params = value

    return locals()


class CompareEngine(GraphGenerator, InputProcessor, DataGenerator, SymbolsInterface):
    params = property(**params())

    @property
    def Categories(self):
        return self._categories

    @property
    def Groups(self):
        return self._groups_by_cat[self._cur_category]
    def get_options_from_groups(self,ls):
        if not ls:
            return []
        s = set()
        for g in ls:
            s = s.union(set(self.Groups[g]))
        return list(s)

    def read_groups_from_file(self):
        try:
            jsongroups= json.load(open(config.JSONFILENAME,'rt'))
            self._groups_by_cat = jsongroups
            self._categories= list(self._groups_by_cat.keys())
            if self._cur_category==None:
                self._cur_category=self._categories[0]
        except:
            print('groups are problem') #raise Exception("error reading groups")

    def __init__(self,filename):
        super(CompareEngine, self).__init__()
        InputProcessor.__init__(self, filename)
        DataGenerator.__init__(self)

        self._annotation=[]
        self._cache_date=None
        self.params=None

        #self._groups = config.GROUPS
        self._catagories=None
        self._cur_category = None
        self.read_groups_from_file()

    def required_syms(self, include_ext=True, want_it_all=False, data_symbols_for_unite=False): #the want it all is in the case of populating dict
        selected = set()
        if data_symbols_for_unite and (self.used_type & Types.COMPARE and self.params.compare_with): #notice that based on params type and not real type
            selected.update(set([self.params.compare_with]))


        if want_it_all and (self.params.unite_by_group & UniteType.ADDPROT):
            selected=set(self.get_portfolio_stocks())

        if self.to_use_ext and include_ext:
            selected.update(set(self.params.ext))
        if (self.params.unite_by_group & ~UniteType.ADDTOTAL) and data_symbols_for_unite:
            print('nontrivla')
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

        requried_syms = self.required_syms(True, True)
        if self._symbols_wanted and (not (set(requried_syms) <= set(self._symbols_wanted))):
            symbols_neeeded= set(requried_syms) - set(self._symbols_wanted)
            print('should add stocks')
            reprocess=1
        else:
            symbols_neeeded=set() #process all...

        B = (1, 0.5)
        if reprocess:
            self.process(symbols_neeeded)
        try:
            self.df, type = self.generate_data()
        except NoDataException:
            print('no data')
            return
        except Exception as e:
            import traceback
            traceback.print_exc()
            e = e
            print('exception in generating data')
            if config.DEBUG:
                pass#raise
            return


        try:
            self.gen_actual_graph(B, list(self.df.columns), self.df, self.params.isline, self.params.starthidden, just_upd, type)
        except TypeError as e:
            e=e
            print("failed generating graph ")




    # makes the entire graph from the default attributes.
    def update_graph(self, params: Parameters = Parameters()):
        reprocess= 1 if  (not self._alldates) else 0

        params.increase_fig=False
        #t = inspect.getfullargspec(CompareEngine.gen_graph)
        #dd={x:self.__getattribute__(x) for x in t.args if x not in ['self','increase_fig','reprocess','just_upd' ] }
        self.gen_graph(params,just_upd=1,reprocess=reprocess )
