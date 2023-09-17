from abc import ABCMeta as NativeABCMeta
from typing import cast, Any, Callable, TypeVar
from abc import abstractmethod,abstractclassmethod,abstractstaticmethod

R = TypeVar('R')


class DummyAttribute:
    pass

def abstract_attribute(obj: Callable[[Any], R] = None) -> R:
    _obj = cast(Any, obj)
    if obj is None:
        _obj = DummyAttribute()
    _obj.__is_abstract_attribute__ = True
    return cast(R, _obj)

class ABCMeta(NativeABCMeta):
    @staticmethod
    def get_properties_names(cls):
        return {k for k, v in vars(cls).items() if isinstance(v, property)}
    def __call__(cls, *args, **kwargs):
        instance = NativeABCMeta.__call__(cls, *args, **kwargs)
        prop = set(ABCMeta.get_properties_names(instance.__class__))
        abstract_attributes = {
            name
            for name in dir(instance)

            if name not in prop and getattr(getattr(instance, name), '__is_abstract_attribute__', False)
        }
        if abstract_attributes:
            raise NotImplementedError(
                "Can't instantiate abstract class {} with"
                " abstract attributes: {}".format(
                    cls.__name__,
                    ', '.join(abstract_attributes)
                )
            )
        return instance
