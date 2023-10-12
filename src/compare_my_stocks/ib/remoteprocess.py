import logging
import os
import subprocess
import time

from common.common import singleton
from config import config

import multiprocessing

@singleton
class RemoteProcess:

    proc=None

    def wait_for_read(cls):
        # if config.Running.StartIbsrvInConsole:

        logging.info("Waiting for IBSourceRem to be ready")
        if not cls.no_ready_file:
            for k in range (config.Running.SleepForIbsrvToStart*10*3):
                time.sleep(0.1)
                try:
                    if open(config.File.IbSrvReady, 'rt').read() == 'ready':
                        break
                except:
                    pass
            else:
                logging.warn("IBSourceRem might not be ready")
                return

        else:
            time.sleep(config.Running.SleepForIbsrvToStart)

        logging.info("IBSourceRem is ready")
    @staticmethod
    def launch_without_console():
        import ibsrv
        return multiprocessing.Pool(1).apply_async(ibsrv.ibsrv)

    def resolve_process(cls):
        if type(config.Sources.IBSource.AddProcess)==str:
            rpath= os.path.abspath(config.Sources.IBSource.AddProcess)
            if not os.path.exists(rpath):
                logging.error(f"IBSRV path reosolved to {rpath} which doesn't exists")
                return False
            else:
                logging.info(f"IBSRV path reosolved to {rpath}")
            v=[rpath]
        else:
            v=  config.Sources.IBSource.AddProcess
        v = ["start", "/wait"] + v
        return v
    def run_additional_process(cls):
        try:
            open(config.File.IbSrvReady, 'w').write('notstarted')
            cls.no_ready_file = False
        except:
            cls.no_ready_file = True



        if os.name != "nt":
            logging.warn("Additional process is only tested on windows. Consider running manually.")
            #cls.proc = subprocess.Popen(v, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, text=True,bufsize=1)
            cls.proc = cls.launch_without_console()
            return True


        if config.Running.StartIbsrvInConsole:
            v= cls.resolve_process()
            if not v:
                return False
            logging.debug("STARTCONS " + str(v))
            cls.proc = subprocess.Popen(v, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, text=True,bufsize=1)
        else:
            logging.debug("STARTNOTCONSOLE")
            cls.proc = cls.launch_without_console()


        return True
         

        # os.spawnle(os.P_NOWAIT,'python',[config.AddProcess])
