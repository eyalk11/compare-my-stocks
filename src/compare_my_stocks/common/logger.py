import logging
from common.loghandler import init_log
from config import config


import inspect
frm = inspect.stack()[2]
mod = inspect.getmodule(frm[0])
log=init_log(mod=mod.__name__ if mod else None,logfile=config.Running.LOGFILE,logerrorfile=config.Running.LOGERRORFILE)
#log=logging.getLogger(mod.__name__) if mod else logging
