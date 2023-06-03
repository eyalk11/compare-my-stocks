import asyncio
import logging
import os
import subprocess
import time

from config import config

def singleton(class_):
    instances = {}
    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]
    return getinstance

@singleton
class RemoteProcess:

    proc=None

    def wait_for_read(cls):
        # if config.Running.START_IBSRV_IN_CONSOLE:
        logging.info("Waiting for IBSourceRem to be ready")
        time.sleep(config.Running.SLEEP_FOR_IBSRV_TO_START)
        logging.info("IBSourceRem is ready")
        #     return
        #
        # if not cls.proc:
        #     logging.error('init process before read')
        #     return None
        # cls.proc.stdout.flush()
        # logging.info("Waiting for IBSourceRem to be ready")
        # l=cls.proc.stdout.readline()
        # if "Ready" in l:
        #     logging.info("IBSourceRem is ready")
        #     return True
        # else:
        #     logging.warn("IBSourceRem might not be ready")
        #
        # logging.debug(l)


    def run_additional_process(cls):
        if type(config.IBConnection.ADDPROCESS)==str:
            rpath= os.path.abspath(config.IBConnection.ADDPROCESS)
            if not os.path.exists(rpath):
                logging.error(f"IBSRV path reosolved to {rpath} which doesn't exists")
                return
            else:
                logging.info(f"IBSRV path reosolved to {rpath}")
            if config.Running.START_IBSRV_IN_CONSOLE:
                v = ["start" ,"/wait" ,rpath]
            else:
                v=[rpath]

        else:
            if config.Running.START_IBSRV_IN_CONSOLE:
                v = ["start" ,"/wait" ]+config.IBConnection.ADDPROCESS
            else:
                v=config.IBConnection.ADDPROCESS

        logging.debug("Running " + str(v))
        cls.proc = subprocess.Popen(v, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, text=True,bufsize=1)

        # os.spawnle(os.P_NOWAIT,'python',[config.ADDPROCESS])
        time.sleep(1)
