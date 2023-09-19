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
    def launch_without_console(command):
        """Launches 'command' windowless and waits until finished"""
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        return subprocess.Popen(command, startupinfo=startupinfo,creationflags = subprocess.CREATE_NO_WINDOW)

    def run_additional_process(cls):
        try:
            open(config.File.IbSrvReady, 'w').write('notstarted')
            cls.no_ready_file = False
        except:
            cls.no_ready_file = True

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

        if os.name != "nt":
            logging.warn("Additional process is only tested on windows. Run ibsrv manually (--ibsrv). ")
            cls.proc = subprocess.Popen(v, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, text=True,bufsize=1)
            return True


        v = ["start", "/wait"] + v
        if config.Running.StartIbsrvInConsole:
            logging.debug("STARTCONS " + str(v))
            cls.proc = subprocess.Popen(v, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, text=True,bufsize=1)
        else:

            v= ["cmd","/c"," ".join(v).replace("/wait","/B /wait")]
            logging.debug("STARTNOTCONSOLE " + str(v))
            # We create here a new process using start , because apperently, IBSRV has errors even !!! if it is started as a normal process.
            # the cmd /c is because it fails to find executable named start.
            cls.proc = cls.launch_without_console(v)

        logging.debug("Running " + str(v))
        return True
         

        # os.spawnle(os.P_NOWAIT,'python',[config.AddProcess])
        time.sleep(1)
