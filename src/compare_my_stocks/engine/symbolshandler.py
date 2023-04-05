import json
import logging

from common.common import simple_exception_handling, Types, UniteType, print_formatted_traceback
from config import config
from engine.parameters import Parameters


class SymbolsHandler:
    def __init__(self):
        self._params : Parameters=None
        self._categories=None
        self._groups_by_cat = {}
        self._cur_category = None
    @simple_exception_handling("error in options")
    def get_options_from_groups(self,ls):

        if not ls:
            return []
        s = set()
        for g in ls:
            if g not in self.Groups:
                raise Exception(f'{g} is not in Groups')
            try:
                s = s.union(set(self.Groups[g]))
            except:
                logging.error("bad group ",g)
                print_formatted_traceback(detailed=False)
                #simple_exception_handling(f"bad group {g}",never_throw=True)()
        if self.params.limit_to_portfolio:
            s=s.intersection(set(self.get_portfolio_stocks()))
        return list(s)

    @simple_exception_handling(err_description='exception in  groups file')
    def read_groups_from_file(self):

            jsongroups= json.load(open(config.File.JSONFILENAME,'rt'))
            self._groups_by_cat = jsongroups
            self._categories= list(self._groups_by_cat.keys())


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
