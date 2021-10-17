from pandas import DataFrame

from config import config
from common.common import NoDataException, UniteType
from processing.datagenerator import DataGenerator
from graph.graphgenerator import GraphGenerator
from input.inputprocessor import InputProcessor
from engine.parameters import Parameters, ParameterError


def params():
    doc = "The params property."

    def fget(self):
        return self._params

    def fset(self, value):
        self._params = value

    return locals()

def first_index_of(ls,fun=None):
    #ls=list(ls)
    if fun==None:
        fun=lambda x:x
    lst=[x for x in range(len(ls)) if fun(ls[x])]
    if lst:
        return lst[0]
    else:
        return -1


class CompareEngine(GraphGenerator, InputProcessor, DataGenerator):
    _groups = config.GROUPS

    @classmethod
    @property
    def Groups(self):
        return CompareEngine._groups

    @staticmethod
    def get_options_from_groups(ls):
        s = set()
        for g in ls:
            s = s.union(set(CompareEngine.Groups[g]))
        return list(s)



    params = property(**params())

    def __init__(self,filename):
        super(CompareEngine, self).__init__()
        InputProcessor.__init__(self, filename)
        DataGenerator.__init__(self)

        self._annotation=[]
        self._cache_date=None
        self.params=None

    def required_syms(self, include_ext=True,want_it_all=False): #the want it all is in the case of populating dict
        selected = set()
        if want_it_all and (self.params.unite_by_group & UniteType.ADDTOTAL):
            selected=set(self.get_portfolio_stocks())

        if not (self.params.unite_by_group & ~UniteType.ADDTOTAL) and self.params.use_groups:
            return selected.union(self.get_options_from_groups(self.params.groups))


        if self.params.use_ext and include_ext:
            selected.update(set(self.params.ext))
        try:
            if self.params.use_groups:
                if self.params.groups:
                    for g in self.params.groups:
                        selected.update((set(self.Groups[g])))
            else:
                selected.update(self.params.selected_stocks)
        except KeyError:
            raise ParameterError("groups")
        return selected
        #t = inspect.getfullargspec(CompareEngine.gen_graph)  # generate all fields from paramters of gengraph
        #[self.__setattr__(a, d) for a, d in zip(t.args[1:], t.defaults)]

    def gen_graph(self, params: Parameters, just_upd=0, reprocess=1):
        if just_upd and self.params:
             self.params.update_from(params)
        else:
            self.params=params

        self.params._baseclass=self

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
