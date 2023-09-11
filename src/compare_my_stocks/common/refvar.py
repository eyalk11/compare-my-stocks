import inspect
import types
from functools import partial
from typing import TypeVar
from typing import Generic

from common.common import neverthrow


def refproperty(var,value=None):
    def getp(self):
        return getattr(self,'_'+var).get(self)

    def setp(self,v):
        return getattr(self,'_'+var).set(self,v)

    def decorator(klass):
        orginit=klass.__init__
        setattr(klass,var,property(getp,setp))

        def newinit(self,*args,**kw):
            rv=RefVar(value)
            setattr(self,'_'+var,rv)
            orginit(self,*args,**kw)

        klass.__init__=newinit
        return klass
    return decorator
T = TypeVar('T')
class M_A(type): pass

class RefVar():
    metaclass = M_A
    def __init__(self, value=None):
        self.value = value
    def get(self,*args):
        return self.value
    def set(self, value):
        self.value = value

    def __getattribute__(self, name):
        if name in ['value','set','get']:
            return object.__getattribute__(self, name)
        else:
            return getattr(self.value, name)



def gen(cls,k, selff, *x, **y):
    print(cls,k, selff,x, (y))
    return (getattr(cls, k))(getattr(selff,'value'), *x, **y)
class GenRefVar(Generic[T]):

    def __call__(self,value=None):
        #RefVar.__metaclass__ = T.__metaclass__
        cls= self.__orig_class__.__args__[0]



        nt= type('RefVarInst', (RefVar,), {})

        d={k:  types.MethodType(partial(gen,cls,k),nt) for k in dir(cls) if callable(getattr(cls,k)) and not inspect.ismethod(getattr(cls,k)) }
        d.pop('__new__')
        d.pop ('__setattr__')
        d.pop('__class__')
        d.pop('__init__')
        d.pop('__dir__')
        d.pop('__init_subclass__')
        d.pop('__str__')
        d.pop('__repr__')
        d.pop('__getattribute__')

        for k,v in d.items():
            setattr(nt,k,v)
        return  nt(True)


        #d= {k:v for k,v in d.items() if v is not None}

        #for k,v in dict(RefVar.__dict__).items():
        #    if k not in d or k in ['__init__','__new__','__getattribute__']:
        #       d[k]=v



        #return RefVar(value)
        #nt = type('RefVar', tuple(), d)
        #return nt(value)

