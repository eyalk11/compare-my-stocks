'''
This file resolves config and presents all its config attributes as globals
'''
import logging
from common.loghandler import init_log
import os
import sys

from common.common import log_conv

CONFIGFILENAME = 'myconfig.py'

MYPROJ='compare_my_stocks'
PROJPATHENV = 'COMPARE_STOCK_PATH'

MYPATH=os.path.dirname(__file__)
datapath=os.path.realpath((os.path.join(MYPATH,'..','data')))
PROJDIR= os.path.join(os.path.expanduser("~"),"."+MYPROJ)

def print_if_ok(*args):
    if 'SILENT' in __builtins__ and  __builtins__['SILENT']==False:
        logging.info(*args)

if not os.path.exists(PROJDIR):
    print_if_ok("""project directory doesn't exists... Creating...
    Consider copying your config files there """)
    print_if_ok(f" cp {datapath}\\* {PROJDIR} ")
    os.makedirs(PROJDIR)

def resolvefile(filename):
    try:
        if filename=='':
            return False,None
        if os.path.isabs(filename):
            return os.path.exists(filename), filename
        for loc in PROJDIR , "/etc/"+MYPROJ, os.environ.get(PROJPATHENV,'didntfind'),datapath,os.curdir:
            fil=os.path.join( loc,filename)
            if os.path.exists(fil):
                return True, os.path.abspath(fil)

        return False, os.path.join( PROJDIR,filename) #default location
    except:
        return False,None
def resolve_it(f):
    if not f in globals():
        print_if_ok(f'You must have {f} in config')
        sys.exit(-1)
    res, fil=resolvefile(globals()[f])

    if fil==None:
        print_if_ok(f'Invalid value {f}')
        return

    if res==False:
        print_if_ok(f'Failed resolving {f}. Using: {fil}')
    else:
        print_if_ok(f'{f} resolved to {fil}')

    globals()[f]=fil



res,config_file=resolvefile(CONFIGFILENAME)


if not res:
    print_if_ok('No config file, aborting')
    sys.exit(-1)

with open(config_file) as f:
    code = compile(f.read(), config_file, 'exec')
    exec(code, globals(), locals())
for x in ['LOGFILE','LOGERRORFILE']:
    resolve_it(x)

try:
    init_log(logfile=LOGFILE,logerrorfile=LOGERRORFILE)
except:
    logging.error("initialize logging failed!")
print_if_ok(log_conv("Using Config File: " , config_file))



FILE_LIST_TO_RES=["HIST_F","HIST_F_BACKUP","JSONFILENAME","SERIALIZEDFILE","REVENUEFILE","INCOMEFILE","COMMONSTOCK","GRAPHFN","DEFAULTNOTEBOOK",'DATAFILEPTR','EXPORTEDPORT']
for f in FILE_LIST_TO_RES:
    resolve_it(f)

