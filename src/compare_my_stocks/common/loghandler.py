import logging
import re
import sys

from common.common import neverthrow

# Implemntation taken from :
# Impacket - Collection of Python classes for working with network protocols.
#
# Copyright (C) 2022 Fortra. All rights reserved.
#
# This software is provided under a slightly modified version
# of the Apache Software License. See the accompanying LICENSE file
# for more information.
#
# Description:
#   This logger is intended to be used by impacket instead
#   of printing directly. This will allow other libraries to use their
#   custom logging implementation.


TRACELEVEL=5

import logging
import os
def dont_print(): #started from jupyter tools
    return logging.getLogger().level == logging.CRITICAL

class MyFormatter(logging.Formatter):
    log_format = 'Run %(run_number)s | %(asctime)s | %(filename)s:%(lineno)d:%(function)s | %(levelname)s | %(message)s'
    run_number=None
    def __init__(self):
        super().__init__(MyFormatter.log_format)

    def format(self, record):
        record.run_number = self.run_number
        record.filename = os.path.basename(record.pathname)
        record.function = record.funcName
        record.lineno = record.lineno
        return super().format(record)




import colorlog

log_colors = {
    "DEBUG": "light_white",
    "INFO": "yellow",
    "WARNING": "blue",
    "ERROR": "red",
    "CRITICAL": "bold_red",
}

class ImpacketFormatter(colorlog.ColoredFormatter):

  '''
  Prefixing logged messages through the custom attribute 'bullet'.
  '''

  def __init__(self,**kwargs):

      colorlog.ColoredFormatter.__init__(self,'%(log_color)s%(bullet)s %(filename)s:%(lineno)d | %(message)s',log_colors=log_colors,**kwargs)

  def format(self, record):
    if record.levelno == logging.INFO:
      record.bullet = '[*]'
    elif record.levelno == logging.DEBUG:
      record.bullet = '[+]'
    elif record.levelno == logging.WARNING:
      record.bullet = '[!]'
    else:
      record.bullet = '[-]'

    return logging.Formatter.format(self, record)

class ImpacketFormatterTimeStamp(ImpacketFormatter):
  '''
  Prefixing logged messages through the custom attribute 'bullet'.
  '''
  def __init__(self,**kwargs):
      logging.Formatter.__init__(self,'[%(asctime)-15s] %(filename)s %(bullet)s %(message)s', None, **kwargs)

  def formatTime(self, record, datefmt=None):
      return ImpacketFormatter.formatTime(self, record, datefmt="%Y-%m-%d %H:%M:%S")

class MyFilter(object):
    def __init__(self, level):
        self.__level = level

    def filter(self, logRecord):
        return logRecord.levelno <= self.__level
def init_log_default(config):
    if 'IBSRV' in __builtins__ and __builtins__['IBSRV']:
        logfile = config.Running.IBLogFile
        logerrorfile = config.Running.IBLogErrorFile
    else:
        logfile = config.Running.LogFile
        logerrorfile = config.Running.LogErrorFile
    debug = config.Running.Debug if not dont_print() else False
    if config.Running.NoColor:
        kwargs = {'no_color':True}
    else:
        kwargs = {}

    loglevel = config.Running.LogLevel

    init_log(logfile=logfile,logerrorfile=logerrorfile,debug=debug,kwargs=kwargs,loglevel=loglevel )

def init_log(mod=None,ts=False,logfile=None,logerrorfile=None,debug=0,kwargs={},loglevel=None):
    import matplotlib
    matplotlib.set_loglevel("INFO")
    def set_format(handler):
        if not ts:
            handler.setFormatter(ImpacketFormatter(**kwargs))
        else:
            handler.setFormatter(ImpacketFormatterTimeStamp(**kwargs))
    # We add a StreamHandler and formatter to the root logger
    logging.addLevelName(TRACELEVEL,"TRACE")
    from contextvars import copy_context
    ctx=copy_context()
    context=None
    for k,v in ctx.items():
        if k.name == 'context':
            context=v
            break

    if context =='main':
        if loglevel is not None:
            logging.getLogger().setLevel(loglevel)
        elif debug and not dont_print():
            logging.getLogger().setLevel(logging.DEBUG)
        #logging.getLogger('Voila').setLevel(logging.DEBUG)

    log=logging.getLogger(mod)
    log.setLevel(logging.getLogger().level)
    log.handlers.clear()

    handler = colorlog.StreamHandler(sys.stdout)
    set_format(handler)
    log.addHandler(handler)
    last_run = 0
    if logfile and MyFormatter.run_number is None:
        if os.path.exists(logfile):
            for z in open(logfile):
                 last_run=max(last_run,neverthrow(lambda: int(re.search('Run (\d+) \|',z).group(1)),default=0))

        last_run+=1
        MyFormatter.run_number=last_run

    if logfile:
        fh = logging.FileHandler(logfile)
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(MyFormatter())
        log.addHandler(fh)
    if logerrorfile:
        if not logfile:
            MyFormatter.run_number= 'UNK'
        ch = logging.FileHandler(logerrorfile)
        ch.setLevel(logging.ERROR)
        fh.setFormatter(MyFormatter())
        log.addHandler(ch)

    log.debug(f'init_log {kwargs}') 


    # Found to work. Not the best.

    # init_log()
    return log

    #logging.getLogger().setLevel(logging.INFO)


