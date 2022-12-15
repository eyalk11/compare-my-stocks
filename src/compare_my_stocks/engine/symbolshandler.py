import json

from common.common import simple_exception_handling, Types, UniteType
from config import config
from engine.parameters import Parameters


class SymbolsHandler:
    def __init__(self):
        self._params : Parameters=None
        self._categories=None
        self._groups_by_cat = {}
        self._cur_category = None

    def get_options_from_groups(self,ls):

        if not ls:
            return []
        s = set()
        for g in ls:
            if g not in self.Groups:
                raise Exception(f'{g} is not in Groups')

            s = s.union(set(self.Groups[g]))
        if self.params.limit_to_portfolio:
            s=s.intersection(set(self.transaction_handler.get_portfolio_stocks()))
        return list(s)

    @simple_exception_handling(err_description='exception in  groups file')
    def read_groups_from_file(self):

            jsongroups= json.load(open(config.JSONFILENAME,'rt'))
            self._groups_by_cat = jsongroups
            self._categories= list(self._groups_by_cat.keys())

    def  required_syms(self, include_ext=True, want_portfolio_if_needed=False, want_unite_symbols=False,only_unite=False):
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
    def params(self) -> Parameters:
        return self._params

    @params.setter
    def params(self,value : Parameters):
        self._params = value

    @property
    def Groups(self):
        return self._groups_by_cat[self.cur_category]
