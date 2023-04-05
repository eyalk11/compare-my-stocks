import logging
from . import newconfig
from .newconfig import resolvefile,Config,ConfigLoader
config : Config = ConfigLoader.main()
