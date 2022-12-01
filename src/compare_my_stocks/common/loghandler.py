import logging
import sys

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

def init_log(ts=False):
    if hasattr(logging,'inited'):
        return
    # We add a StreamHandler and formatter to the root logger
    logging.addLevelName(TRACELEVEL,"TRACE")
    handler = colorlog.StreamHandler(sys.stdout)
    if not ts:
        handler.setFormatter(ImpacketFormatter())
    else:
        handler.setFormatter(ImpacketFormatterTimeStamp())
    logging.getLogger().addHandler(handler)
    logging.inited=1
    #logging.getLogger().setLevel(logging.INFO)