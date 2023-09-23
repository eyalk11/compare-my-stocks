from __future__ import annotations
'''
Allows for composition with currying 
In[38]: C /  list / map % (lambda x: x*2) @  range(1,5)
Out[38]: [2, 4, 6, 8]
In [109]: C / list/ zip &  C / list  @ range(5) ^ [4,8,9,10,11]
Out[109]: [(0, 4), (1, 8), (2, 9), (3, 10), (4, 11)]
So, / is composition , % is partial (nice trick) and @ is applying.

& is partial but in lower precedence .
^ is applying with lower precedence

'''
from typing import Callable, Generic, ParamSpec, TypeVar
from enum import Enum

import inspect
from functools import partial
from inspect import _ParameterKind, signature

dictfilt = lambda x, y: dict([(i, x[i]) for i in x if i in set(y)])

T = TypeVar('T')
P = ParamSpec('P')
Q = ParamSpec('Q')
U = TypeVar('U')
class UnsafeType(Enum):
    NotSafe= 0
    Safe= 1
    SafeWithFuncs=2 
class CInst(Generic[P,T]):
    def __init__(self,func :Callable[P,T],unsafe : UnsafeType  =UnsafeType.NotSafe):
        self.func=func
        self._unsafe= unsafe
    def __truediv__(self,other :Callable[Q,P.args]) -> CInst[Q,T] :
        def inner(*args: Q.args, **kwargs: Q.kwargs) -> T:
            return self.func(other(*args,**kwargs))
        if type(other) == str:
            other=eval("lambda x: " + other)
        return CInst(inner)

    def __and__(self,other):
        return self.__mod__(other)

    def __xor__(self,other):
        return self.__matmul__(other)

    def __call__(self,*args: P.args, **kwargs: P.kwargs) -> T:
        return self.func(*args,**kwargs)

    def __matmul__(self,other) -> T:
        if (type(other) == tuple):
            return self.func(*other)
        elif (type(other) == dict):
            return self.func(**other)
        else:
            return self.func(other)

    def __mod__(self, other):
        def handle_currying():
            origsig = signature(self.func)
            f = partial(self.func, **other)
            sig = signature(f)
            newparams = {}
            mapped_to_func = {}
            nother = other.copy()
            s = set()
            lambda_dic = dict() 
            if self._unsafe == UnsafeType.NotSafe: 
                for k,v in other.items():
                    if type(v)==str and v.startswith('->'):
                        lambda_dic[k]= f'{v.replace("->","")}'

            # We start from regular
            for k, v in sig.parameters.items():
                if inspect.isfunction(v.default):
                    s.add(k)
                    p = signature(v.default).parameters
                    newparams.update(p.items())
                    mapped_to_func[k] = (v.default, set([k for k in p]))
                    nother.pop(k)
                elif k in lambda_dic: 
                    nother.pop(k)
                    
            origparams = {k: v for k, v in sig.parameters.items() if k not in s}
            newparams.update(origparams)

            # partial makes some args keyword only
            for k, v in origparams.items():
                if v.kind == _ParameterKind.KEYWORD_ONLY:
                    if origsig.parameters[k].kind == _ParameterKind.POSITIONAL_OR_KEYWORD:
                        newparams[k] = inspect.Parameter(k, _ParameterKind.POSITIONAL_OR_KEYWORD,
                                                         default=origsig.parameters[k].default,
                                                         annotation=origsig.parameters[k].annotation)

            nf = partial(self.func, **nother)  # determined values

            newsig = sig.replace(parameters=newparams.values())

            def newfunc(*args, **kwargs):
                b = newsig.bind(*args, **kwargs)
                b.apply_defaults()
                ntobind = {}

                for k, v in mapped_to_func.items():
                    func, args = v
                    dic = (dictfilt(b.arguments, args))
                    ntobind[k] = func(**dic)  # we removed from nf the
                for k,v in lambda_dic.items():
                    s.add(k)
                    print(v)
                    ntobind[k]=eval(v,b.arguments)

                for k, v in b.arguments.items():
                    if k not in ntobind:
                        ntobind[k] = v

                nd = dictfilt(ntobind, signature(nf).parameters.keys())
                return nf(**nd)

            return newfunc

        if (type(other) == tuple):
            fn= partial(self.func,*other)
        elif (type(other) == dict):

            fn= handle_currying() if self._unsafe != UnsafeType.Safe else partial(self.func,**other)


        else:
            fn=partial(self.func, other)
        return CInst(fn,unsafe=self._unsafe)



class CSimpInst(CInst):
    def __init__(self,unsafe=UnsafeType.NotSafe):
        self.func = None
        self._unsafe= unsafe
    def __truediv__(self,other :Callable[Q,U]) -> CInst[Q,U] :
        return CInst(other,unsafe=self._unsafe)
    def __call__(self):
        raise NotImplementedError()


C=CSimpInst()
CS=CSimpInst(unsafe=UnsafeType.Safe)

# U = TypeVar('U')


#def f(a,b,c):
#    return (a,b,c)
#g=  (CS / f % {'b': "->b*a*2"} @ (3, 7))
#g=g
#print(g)
