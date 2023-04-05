import sys
import win32api
if 'ipykernel_launcher' in sys.argv:
    print(('strangeeee'))
    if sys.path[0] == '':
        del sys.path[0]

    from ipykernel import kernelapp as apip
    app.launch_new_instance()

    sys.exit(0)

#cheating...
try:
    __builtins__.SILENT=False
except:
    pass

from compare_my_stocks import main
import subprocess


main()



