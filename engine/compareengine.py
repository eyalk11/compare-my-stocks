from config import config
from common.common import NoDataException
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
        self._alldates=None
        self._fset=set()
        self._annotation=[]
        self._cache_date=None
        self.params=None

        #t = inspect.getfullargspec(CompareEngine.gen_graph)  # generate all fields from paramters of gengraph
        #[self.__setattr__(a, d) for a, d in zip(t.args[1:], t.defaults)]

    def gen_graph(self, params: Parameters, just_upd=0, reprocess=1):
        if just_upd and self.params:
             self.params.update_from(params)
        else:
            self.params=params

        self.params._baseclass=self

        if self.params.selected_stocks and not self.params.use_groups:
            if not ( set(self.params.selected_stocks)<=set(self._symbols_wanted)):
                print('should add stocks')
                reprocess=1

        B = (1, 0.5)
        if reprocess:
            self.process()
        try:
            self.dt,type = self.generate_data()
        except NoDataException:
            print('no data')
            return
        except Exception as e:
            import traceback
            traceback.print_exc()
            e = e
            print('exception in generating data')
            return


        self.cols = list(self.dt)

        try:
            self.gen_actual_graph(B, self.cols, self.dt,  self.params.isline, self.params.starthidden,just_upd,type)
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
