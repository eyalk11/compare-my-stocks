import Pyro5.server

from config import config
from input.ibsource import IBSourceRem

class MyDeamon(Pyro5.server.Daemon):
    def clientDisconnect(self,conn):
        print('called')
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