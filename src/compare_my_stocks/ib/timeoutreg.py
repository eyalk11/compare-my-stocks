import asyncio

from Pyro5.api import register_class_to_dict, register_dict_to_class


def thingy_class_to_dict(obj):
    return { "__class__": "waheeee-custom-thingy",
        "timeouterror":1
             }


def thingy_dict_to_class(classname, d):
    return TimeoutError()

register_class_to_dict(asyncio.exceptions.TimeoutError, thingy_class_to_dict)

register_dict_to_class("waheeee-custom-thingy", thingy_dict_to_class)