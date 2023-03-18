import logging
import sys
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

  def __init__(self):

      colorlog.ColoredFormatter.__init__(self,'%(log_color)s%(bullet)s %(filename)s | %(message)s',log_colors=log_colors)

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
  def __init__(self):
      logging.Formatter.__init__(self,'[%(asctime)-15s] %(filename)s %(bullet)s %(message)s', None)

  def formatTime(self, record, datefmt=None):
      return ImpacketFormatter.formatTime(self, record, datefmt="%Y-%m-%d %H:%M:%S")

class MyFilter(object):
    def __init__(self, level):
        self.__level = level

    def filter(self, logRecord):
        return logRecord.levelno <= self.__level

def init_log(mod=None,ts=False,logfile=None,logerrorfile=None):
    def set_format(handler):
        if not ts:
            handler.setFormatter(ImpacketFormatter())
        else:
            handler.setFormatter(ImpacketFormatterTimeStamp())
    # We add a StreamHandler and formatter to the root logger
    logging.addLevelName(TRACELEVEL,"TRACE")
    log=logging.getLogger(mod)
    log.handlers.clear()

    handler = colorlog.StreamHandler(sys.stdout)
    set_format(handler)
    log.addHandler(handler)
    if logfile:
        fh = logging.FileHandler(logfile)
        fh.setLevel(logging.DEBUG)
        set_format(fh)
        log.addHandler(fh)
    if logerrorfile:
        ch = logging.FileHandler(logerrorfile)
        ch.setLevel(logging.ERROR)
        set_format(ch)
        log.addHandler(ch)
    return log

    #logging.getLogger().setLevel(logging.INFO)


