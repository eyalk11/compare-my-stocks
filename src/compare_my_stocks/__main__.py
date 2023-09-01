import sys
import win32api
if 'ipykernel_launcher' in sys.argv:
    print(('strangeeee'))
    if sys.path[0] == '':
        del sys.path[0]

    from ipykernel import kernelapp as app
    app.launch_new_instance()

    sys.exit(0)

#cheating...
try:
    __builtins__['SILENT']=False
except:
    pass
#cheating...
try:
    __builtins__.SILENT=False
except:
    pass


from compare_my_stocks import MainClass
import subprocess


if __name__ == "__main__":
    import argparse

    # Create the parser
    parser = argparse.ArgumentParser()
    # Add the console switch
    parser.add_argument('--console', action='store_true', help='Enable console')
    # Add the ibconsole switch
    parser.add_argument('--ibconsole', action='store_true', help='Enable ibconsole')
    parser.add_argument('--debug', action='store_true', help='Enable debug')
    parser.add_argument('--ibsrv', action='store_true', help='Use ibsrv instead')
    # Parse the command-line arguments
    args = parser.parse_args()

    if args.ibsrv: 
        from compare_my_stocks import ibsrv
    else:
        MainClass().main(args.console,args.ibconsole,args.debug)
