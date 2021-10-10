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

class RefVar(object):
    def __init__(self, value=None):
        self.value = value
    def get(self,*args):
        return self.value
    def set(self,main, value):
        self.value = value

