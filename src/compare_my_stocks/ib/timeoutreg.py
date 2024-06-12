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

import ib_async


def class_to_dict(obj):

    return { "__class__": "reqerror",
             "reqid": obj.reqId,
                "code": obj.code,
                "message": obj.message
             }


def dict_to_class(classname, d):
    return ib_async.wrapper.RequestError(code=d['code'], message=d['message'], reqId=d['reqid'])
register_dict_to_class("reqerror", dict_to_class)
register_class_to_dict(ib_async.wrapper.RequestError, class_to_dict)

