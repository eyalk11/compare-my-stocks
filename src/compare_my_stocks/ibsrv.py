import asyncio
import logging

import Pyro5.server

try:
    __builtins__['IBSRV']=True # A hack to make the system know it is IBSRV (for logging).
except:
    __builtins__.IBSRV = True


from config import config
from ib.timeoutreg import thingy_class_to_dict, thingy_dict_to_class
from input.ibsource import IBSourceRem, IBSourceRemGenerator
from ib import timeoutreg

from Pyro5.api import register_class_to_dict, register_dict_to_class






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
daemon = MyDeamon(host="localhost",port=config.Sources.IBSource.IBSRVPORT)                # make a Pyro daemon
uri = daemon.register(IBSourceRemGenerator,objectId="aaa")   # register the greeting maker as a Pyro object



print("Ready. Object uri =", uri)      # print the uri so we can use it in the client later
logging.debug("writing ",config.File.IBSRVREADY)
try:
    open(config.File.IBSRVREADY,'wt').write('ready')
except:
    logging.debug("Could not write ready file")
logging.info("IBSRV Started")
daemon.requestLoop()                   # start the event loop of the server to wait for calls
