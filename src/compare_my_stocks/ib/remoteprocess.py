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
        if not cls.no_ready_file:
            while 1:
                time.sleep(0.1)
                try:
                    if open(config.File.IBSRVREADY, 'rt').read() == 'ready':
                        break
                except:
                    pass

        else:
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
    @staticmethod
    def launch_without_console(command):
        """Launches 'command' windowless and waits until finished"""
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        return subprocess.Popen(command, startupinfo=startupinfo,creationflags = subprocess.CREATE_NO_WINDOW)

    def run_additional_process(cls):
        try:
            open(config.File.IBSRVREADY, 'w').write('notstarted')
            cls.no_ready_file = False
        except:
            cls.no_ready_file = True

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
            v = ["start" ,"/wait" ]+config.IBConnection.ADDPROCESS
            if config.Running.START_IBSRV_IN_CONSOLE:
                cls.proc = subprocess.Popen(v, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, text=True,bufsize=1)
            else:
                v= ["cmd","/c"," ".join(v).replace("/wait","/B /wait")]
                # We create here a new process using start , because apperently, IBSRV has errors even !!! if it is started as a normal process.
                # the cmd /c is because it fails to find executable named start.
                cls.proc = cls.launch_without_console(v)

        logging.debug("Running " + str(v))
         

        # os.spawnle(os.P_NOWAIT,'python',[config.ADDPROCESS])
        time.sleep(1)
