from __future__ import annotations

import typing

'''
Allows for composition with currying 
In[38]: C /  list / map % (lambda x: x*2) @  range(1,5)
Out[38]: [2, 4, 6, 8]
In [109]: C / list/ zip &  C / list  @ range(5) ^ [4,8,9,10,11]
Out[109]: [(0, 4), (1, 8), (2, 9), (3, 10), (4, 11)]
So, / is composition , % is partial (nice trick) and @ is applying.

& is partial but in lower precedence .
^ is applying with lower precedence
// is applying with currying. Which means is carries the arguments to the next function, if needed.  
Partial supports function assigment which means you can do:
 def f(a,b,c):
    return (a,b,c) 
 f % {'b': "->b*a*2"} @ (1,3) 
 or f (lambda b: b*2}
 
 Which only apply the lambda on the relvant part of the eq .
 Use UnsafeType.Safe or disable UnsafeType.WithFuncs so that it would use vanila partial.      
 Notice that using -> syntax is really unsafe . 
 
 
 C / [1,2,3,4] @ func -> func(1,2,3,4) 
C / [1,2,3,4]  << func -> [func(1) , func(2) , ] 
'''
from typing import Callable, Generic, ParamSpec, TypeVar
from enum import Enum, Flag

import inspect
from functools import partial
from multimethod import overload		 as singledispatchmethod, overload	 as singledispatch

from inspect import _ParameterKind, signature

dictfilt = lambda x, y: dict([(i, x[i]) for i in x if i in set(y)])
dictnfilt = lambda x, y: dict([(i, x[i]) for i in x if not(i in set(y))])

T = TypeVar('T')
P = ParamSpec('P')
Q = ParamSpec('Q')
U = TypeVar('U')
class UnsafeType(Flag):
    NotSafe= 0
    Safe= 1
    WithFuncs=2
    Currying=4
#from functools import singledispatch

class CInst(Generic[P,T]):
    @singledispatch
    def __init__(self,func :Callable[P,T],prev :CInst = None, unsafe : UnsafeType  =UnsafeType.NotSafe):
        self.func=func
        self._unsafe= unsafe
        self.prev=prev
        self.origargs=None
        self.col=None
    @__init__.register
    def __init(self,other: typing.Collection | typing.Generator,unsafe : UnsafeType  =UnsafeType.NotSafe):
        self.col=other
        self._unsafe=unsafe

    @singledispatchmethod
    def __floordiv__(self,other :Callable[Q,P]) -> CInst[Q,T] :
        return CInst(other,self,self._unsafe | UnsafeType.Currying)
    @__floordiv__.register
    def __floordiv__(self,other: str) -> CInst[Q, T]:
        if self._unsafe & UnsafeType.Safe == UnsafeType.NotSafe:
            return self.__floordiv__(CInst.conv_str_to_func(other),self._unsafe)
        else:
            raise "cant do it when safe"

    # def __getattr__(self, item):
    #     if self.col is not None:
    #         return getattr(self.col,item)
    def __eq__(self, other):
        if type(other) is CInst:
            return self.func==other.func and self.col==other.col

        if self.col is not None:
            return self.col==other
        return self.func==other

    def apply(self,origargs,args) -> T:
        def basic(args):
            if self.prev is None:
                return self.func(**args)
            return self.prev.apply(origargs,self.func(**args))
        if self.func is None:
            return args
        if type(args)!=dict:
            b=self.get_args(args)
            args=b.arguments

        if self._unsafe & UnsafeType.Currying != UnsafeType.Currying:
            if self.prev is None:
                return self.func(**args)
            return self.prev.apply(origargs,self.func(**args))
        else:
            try:
                sig = signature(self.func)
                b = sig.bind(**args)
            except TypeError:

                add_args= dictfilt(dictnfilt(origargs,args),sig.parameters.keys())
                args.update(add_args)
                return basic(args)
            return basic(args)



    @singledispatch
    def __truediv__(self,other :Callable) -> CInst :
        return CInst(other, self, self._unsafe & (~UnsafeType.Currying))

    @__truediv__.register
    def __truediv__(self, other: typing.Collection) -> CInst[Q, T]:
        return CInst(other,self._unsafe)

    @__truediv__.register
    def __truediv__(self,other: str) -> CInst[Q, T]:
        if self._unsafe & UnsafeType.Safe == UnsafeType.NotSafe:
            return self.__truediv__(CInst.conv_str_to_func(other))
        else:
            raise "cant do it when safe"
    def __and__(self,other):
        return self.__mod__(other)

    def __xor__(self,other):
        return self.__matmul__(other)

    def __call__(self,*args: P.args, **kwargs: P.kwargs) -> T:
        return self.func(*args,**kwargs)

    @singledispatchmethod
    def __matmul__(self,other) -> T:

        return self.tmpapply(other)

    def tmpapply(self, other):
        b = self.get_args(other)
        return self.apply(b.arguments, b.arguments)

    @__matmul__.register
    def __matmul__(self,other: typing.Callable) -> T:
        if self.col is None:
            return self.tmpapply(other)
        if type( self.col) is dict:
            return other(**self.col)
        else:
            return other(*self.col)
    @staticmethod
    def conv_str_to_func(st):
        if st.startswith('->'):
            return eval('lambda x:' + st[2:])
    @__matmul__.register
    def __matmul__(self,other: str) -> T:
        if self.col is None:
            return self.tmpapply(other)
        if self._unsafe & UnsafeType.Safe == UnsafeType.NotSafe:
            return self.__matmul__(CInst.conv_str_to_func(other))
        else:
            raise "cant do it when safe"




    def __lshift__(self, other : Callable):
        if self.col is None:
            raise ValueError('Can only use << on collection')
        def gen():
            for  k in self.col:
                yield other(k)

        return CInst(gen(), self._unsafe)




    def get_args(self, other):
        if (type(other) in [tuple, list]):
            b = signature(self.func).bind_partial(*other)
        elif (type(other) == dict):
            b = signature(self.func).bind_partial(**other)
        else:
            b = signature(self.func).bind_partial(other)
        return b

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
            if self._unsafe & UnsafeType.Safe == UnsafeType.NotSafe:
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

            fn= handle_currying() if self._unsafe & UnsafeType.WithFuncs == UnsafeType.WithFuncs else partial(self.func,**other)


        else:
            fn=partial(self.func, other)
        return CInst(fn,self,unsafe=self._unsafe)



class CSimpInst(CInst):
    def __init__(self,unsafe=UnsafeType.NotSafe | UnsafeType.WithFuncs):
        self.func = None
        self._unsafe= unsafe
        self.prev=None
        self.col  =None
    def __call__(self):
        raise NotImplementedError()


C=CSimpInst()
CS=CSimpInst(unsafe=UnsafeType.Safe)

# U = TypeVar('U')

