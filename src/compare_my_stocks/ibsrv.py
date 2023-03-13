import asyncio

import Pyro5.server
from Pyro5.serializers import SerpentSerializer

from config import config
from input.ibsource import IBSourceRem


from Pyro5.api import register_class_to_dict, register_dict_to_class


def thingy_class_to_dict(obj):
    return { "__class__": "waheeee-custom-thingy",
        "timeouterror":1
             }
def thingy_dict_to_class(classname, d):
    return TimeoutError()

register_class_to_dict(asyncio.exceptions.TimeoutError, thingy_class_to_dict)

register_dict_to_class("waheeee-custom-thingy", thingy_dict_to_class)




class MyDeamon(Pyro5.server.Daemon):
    def clientDisconnect(self,conn):
        print(('disc called'))
        IBSourceRem.on_disconnect()
        # v=list(self.objectsById.values())
        # if len(v)>0:
        #
        #     x : IBSourceRem =v[0]
        #     x.on_disconnect()
#Pyro5.server.config.SERIALIZER='marshal'
Pyro5.server.config.SERVERTYPE="multiplex"
Pyro5.server.config.DETAILED_TRACEBACK=True
daemon = MyDeamon(host="localhost",port=config.IBSRVPORT)                # make a Pyro daemon
uri = daemon.register(IBSourceRem,objectId="aaa")   # register the greeting maker as a Pyro object

print("Ready. Object uri =", uri)      # print the uri so we can use it in the client later
daemon.requestLoop()                   # start the event loop of the server to wait for calls
