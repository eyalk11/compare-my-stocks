
import os
import sys

MYPROJ='compare_my_stocks'
PROJPATHENV = 'COMPARE_STOCK_PATH'

def resolvefile(filename):
    try:
        if filename=='':
            return None
        if os.path.isabs(filename):
            return filename
        for loc in './data/', os.curdir, os.path.join(os.path.expanduser("~"),"."+MYPROJ), "/etc/"+MYPROJ, os.environ.get(PROJPATHENV,'didntfind'):
            fil=os.path.join( loc,filename)
            if os.path.exists(fil):
                return fil
        return None
    except:
        return None

config_file=resolvefile('myconfig.py')
print(config_file)

with open(config_file) as f:
    code = compile(f.read(), config_file, 'exec')
    exec(code, globals(), locals())
print(JSONFILENAME)
FILE_LIST_TO_RES=["HIST_F","HIST_F_BACKUP","JSONFILENAME","SERIALIZEDFILE","REVENUEFILE","INCOMEFILE","COMMONSTOCK","GRAPHFN","PORTFOLIOFN"]
for f in FILE_LIST_TO_RES:
    if not f in globals():
        print(f'You must have {f} in config')
        sys.exit(-1)
    fil=resolvefile(globals()[f])
    if fil==None:
        print(f'failed resolving {f}')
    globals()[f]=fil


print(JSONFILENAME)