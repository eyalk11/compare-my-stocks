import inspect
import logging
import os
from functools import partial

from Pyro5.errors import format_traceback, get_pyro_traceback

try:
    from ib_insync.wrapper import RequestError
    from ibflex.client import BadResponseError
    default_not_detailed_errors = [ConnectionRefusedError,TimeoutError,
        ValueError,NotImplementedError,BadResponseError,RequestError]
except:
    default_not_detailed_errors = [
        ConnectionRefusedError,TimeoutError,ValueError,NotImplementedError]


# don't import config here

def format_traceback_str(*args,detailed=True):
    return (''.join([x[:500] for x in format_traceback(*args,detailed=detailed)]))


def print_formatted_traceback(detailed=True):
    logging.error(format_traceback_str(detailed=detailed))


def get_caller_info(over):
    return "aa",2
    frame = inspect.stack()[over]
    filename = frame.filename
    line_number = frame.lineno
    return os.path.basename(filename), line_number


class SimpleExceptionContext:
    ISWING=None

    def __init__(self, err_description=None,return_succ=None,never_throw=False,always_throw=False,debug=False,detailed=True,err_to_ignore=[],callback=None,noconfig=False,caller=None,logf=None):
        self.err_description=err_description
        self.return_succ=return_succ
        self.never_throw=never_throw
        self.always_throw=always_throw
        self.debug=debug
        self.detailed=detailed
        self.err_to_ignore=err_to_ignore
        self.callback=callback
        self.nocfg=noconfig
        if caller is None:
            caller= get_caller_info(2)
        self.caller=caller
        self.logf=logf

    def checkwing(self):
        if SimpleExceptionContext.ISWING is not None:
            return SimpleExceptionContext.ISWING

        import psutil

        # Get the current process
        current_process = psutil.Process()
        # Get the parent process
        parent_process = current_process.parent()
        # Get the name of the parent process
        parent_process_name = parent_process.name()
        SimpleExceptionContext.ISWING= 'wing' in parent_process_name
        return SimpleExceptionContext.ISWING

    def __enter__(self):
        # Code to be executed when entering the context
        tostop = os.environ.get('PYCHARM_HOSTED') == '1' or self.checkwing()
        if not self.nocfg:
            try:
                from config import config
                tostop=tostop and config.Running.StopExceptionInDebug
                if config.Running.IsTest:
                    tostop = True
                self.config = config
            except:
                self.config=None
        else:
            self.config=None
            # logging.debug("error loading config in simple exception handling. Probably fine.")

        self.do_nothing= tostop and not self.never_throw and self.return_succ is None

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # Code to be executed when exiting the context
        if self.do_nothing:
            return False

        if exc_value is None:
            return False
        try:
            if self.callback is not None:
                self.callback(exc_value)
        except:
            logging.warn("error in callback {} ".format(self.callback))
        if exc_type is not None:
            # Handle any exceptions raised within the context
            # Propagate any exceptions raised within the context
            return self.on_exception(exc_type,exc_value,traceback)

    def on_exception(self, exc_type, exc_value, traceback):
        e=exc_value
        # TmpHook.GetExceptionHook().emit(e)
        if exc_type in self.err_to_ignore and not self.never_throw:
           return False  # throw
        if self.logf is None:
            logf = logging.debug if self.debug else logging.error
        else:
            logf = self.logf
        tmpst = format_traceback_str(exc_type, exc_value, traceback , detailed=self.detailed)
        strng = "# if you see this in your traceback, you should probably inspect the remote traceback as well"
        if strng in tmpst and e.__class__ not in default_not_detailed_errors:
            logf(("".join(get_pyro_traceback())))
        if self.err_description:
            logf( '%s:%s' % (self.caller)  + ' ' + str(self.err_description))
        if self.err_description is None:
            logf( '%s:%s' % (self.caller)  + ' ' + str(e))
        if self.config is not None and self.config.Running.IsTest:
            logf(format_traceback_str(exc_type,exc_value, traceback, detailed=self.detailed))  # just in case
        elif e.__class__ not in default_not_detailed_errors and self.detailed:
            logf(format_traceback_str(exc_type,exc_value, traceback, detailed=self.detailed))
        else:
            logf('%s %s ' % (e.__class__ ,str(e))  )
        if self.always_throw:
           return False #throw
        return True

def excp_handler(exc_type,handler=lambda a,b: None):
    def decorated(func):
        if hasattr(func,'errors_to_handle'):
            func.errors_to_handle+= [exc_type]
        else:
            func.errors_to_handle=[exc_type]

        def internal(*args,**kwargs):
            try:
                return func(*args,**kwargs)
            except exc_type as e:
                handler(args[0],e) #args[0] is self in this case
        return internal
    return decorated

def simple_exception_handling(err_description=None,return_succ='undef',never_throw=False,always_throw=False,debug=False,detailed=True,err_to_ignore=[],callback=None,noconfig=False,logf=None):
    def decorated(func):
        caller = get_caller_info(2)
        def internal(*args,**kwargs):
            nonlocal err_to_ignore,logf

            no_exception = False
            ret=None
            if hasattr(decorated,'errors_to_handle'):
                err_to_ignore+=decorated.errors_to_handle
            try:
                with SimpleExceptionContext(err_description=err_description,return_succ=return_succ,never_throw=never_throw,always_throw=always_throw,debug=debug,detailed=detailed,err_to_ignore=err_to_ignore,callback=callback,noconfig=noconfig,caller=caller,logf=logf):
                    from common.loghandler import TRACELEVEL
                    logging.log(level=TRACELEVEL, msg=f"called: {err_description} {func}")
                    ret= func(*args,**kwargs)
                    logging.log(level=TRACELEVEL, msg=f"after: {err_description} {func}")

                    no_exception = True
            except Exception as e:
                if hasattr(decorated, 'errors_to_handle'):
                    if e.__class__ in decorated.errors_to_handle:
                        logf = logging.debug if debug else logging.error
                        logf(err_description) # a bit of an hack
                        #excp handler can't know about description ...
                raise

            if not no_exception and return_succ!='undef':
                return return_succ
            return ret

        return internal


    return decorated
