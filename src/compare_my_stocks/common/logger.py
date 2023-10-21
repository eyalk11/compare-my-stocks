import logging
from common.loghandler import init_log
from config import config


import inspect
frm = inspect.stack()[2]
mod = inspect.getmodule(frm[0])
if config.Running.NoColor:
    kwargs = {'no_color':True}
else:
    kwargs = {} 
log=init_log(mod=mod.__name__ if mod else None, logfile=config.Running.LogFile, logerrorfile=config.Running.LogErrorFile,debug=config.Running.Debug, kwargs=kwargs,loglevel=config.Running.LogLevel)
#log=logging.getLogger(mod.__name__) if mod else logging
