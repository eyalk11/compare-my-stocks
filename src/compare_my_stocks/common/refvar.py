from typing import TypeVar
from typing import Generic 
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

class RefVar():
    def __init__(self, value=None):
        self.value = value
    def get(self,*args):
        return self.value
    def set(self, value):
        self.value = value


    def __getattribute__(self, name):
        if name == 'value':
            return object.__getattribute__(self, name)
        else:
            return getattr(self.value, name)

class GenRefVar(Generic[T]):
    @classmethod
    def __call__(self,value=None): 
        nt = type('RefVar', (T,), dict(RefVar.__dict__)) 
        return nt(value)

