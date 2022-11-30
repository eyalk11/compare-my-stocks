import sys

if 'ipykernel_launcher' in sys.argv:
    logging.debug(('strangeeee'))
    if sys.path[0] == '':
        del sys.path[0]

    from ipykernel import kernelapp as app
    app.launch_new_instance()

    sys.exit(0)

#cheating...
__builtins__.SILENT=False

from compare_my_stocks import main
import subprocess


main()



