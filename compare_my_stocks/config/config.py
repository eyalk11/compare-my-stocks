
import os
import sys

MYPROJ='compare_my_stocks'
PROJPATHENV = 'COMPARE_STOCK_PATH'

MYPATH=os.path.dirname(__file__)
datapath=os.path.realpath((os.path.join(MYPATH,'..','data')))
PROJDIR= os.path.join(os.path.expanduser("~"),"."+MYPROJ)
if not os.path.exists(PROJDIR):
    print("""project directory doesn't exists... Creating...
    Consider copying your config files there """)
    print(f" cp {datapath}\\* {PROJDIR} ")
    os.makedirs(PROJDIR)

def resolvefile(filename):
    try:
        if filename=='':
            return False,None
        if os.path.isabs(filename):
            return filename
        for loc in os.curdir, PROJDIR , "/etc/"+MYPROJ, os.environ.get(PROJPATHENV,'didntfind'),datapath:
            fil=os.path.join( loc,filename)
            if os.path.exists(fil):
                return True, fil

        return False, os.path.join( PROJDIR,filename) #default location
    except:
        return False,None

res,config_file=resolvefile('myconfig.py')

if not res:
    print('No config file, aborting')
    sys.exit(-1)
print("Using Config File: " , config_file)

with open(config_file) as f:
    code = compile(f.read(), config_file, 'exec')
    exec(code, globals(), locals())

FILE_LIST_TO_RES=["HIST_F","HIST_F_BACKUP","JSONFILENAME","SERIALIZEDFILE","REVENUEFILE","INCOMEFILE","COMMONSTOCK","GRAPHFN","PORTFOLIOFN"]
for f in FILE_LIST_TO_RES:
    if not f in globals():
        print(f'You must have {f} in config')
        sys.exit(-1)
    res, fil=resolvefile(globals()[f])

    if fil==None:
        print(f'Invalid value {f}')
        continue

    if res==False:
        print(f'Failed resolving {f}. Using: {fil}')
    else:
        print(f'{f} resolved to {fil}')

    globals()[f]=fil


