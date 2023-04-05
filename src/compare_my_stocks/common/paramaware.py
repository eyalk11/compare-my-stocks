import dataclasses

from common.common import smap

'''
Parameters has many default values. Here we want to see what we changed explicitly. In order to be able to merge to parameters. 
'''
from dataclasses import fields

def paramaware(klass):
    orginit=klass.__init__
    orgset = klass.__setattr__
    # def __setstate__(self,state):
    #     return super(klass,self).__setstate__(state)
    def __setstate__(self,state):
        orginit(self)
        self._changed_keys = set(state.keys())

        for slot, value in state.items():
            object.__setattr__(self, slot, value)
    def __nsetattr__(self, name, value):
        if hasattr(self,'_changed_keys') and name in self.__dataclass_fields__.keys(): #you cant set here
            self._changed_keys.add(name)
        return orgset(self,name,value)

    def newinit(self,*args,**kwargs):
        orginit(self,*args,**kwargs)
        self._changed_keys=set(kwargs.keys()).intersection(set(self.__dataclass_fields__.keys())) #TODO: take care of args.



    def update_from(self,another,all=False):
        keys_ = smap(lambda x:x.name,fields(another) )#(set(another._changed_keys) if not all else set(dic.keys()))
        if not all:
            keys_=keys_.intersection(set(self._changed_keys))
        for k in keys_:
            setattr(self,k, getattr(another,k))
        self._changed_keys= keys_

    klass.__init__=newinit
    klass.__setattr__=__nsetattr__
    #klass.__orgsetstate__ = klass.__setstate__
    klass.__setstate__ = __setstate__

    klass.update_from=update_from

    return klass
