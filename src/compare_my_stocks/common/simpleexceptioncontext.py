import logging
import os

from Pyro5.errors import get_pyro_traceback

from Pyro5.errors import format_traceback

default_not_detailed_errors = [ConnectionRefusedError,TimeoutError ]


def format_traceback_str(*args,detailed=True):
    return (''.join([x[:500] for x in format_traceback(*args,detailed=detailed)] ))
def print_formatted_traceback(detailed=True):
    logging.error(format_traceback_str(detailed=detailed))


class SimpleExceptionContext:
    def __init__(self, err_description=None,return_succ=None,never_throw=False,always_throw=False,debug=False,detailed=True,err_to_ignore=[]):
        self.err_description=err_description
        self.return_succ=return_succ
        self.never_throw=never_throw
        self.always_throw=always_throw
        self.debug=debug
        self.detailed=detailed
        self.err_to_ignore=err_to_ignore


    def __enter__(self):
        # Code to be executed when entering the context
        try:
            from config import config
            bol=config.Running.STOP_EXCEPTION_IN_DEBUG
            if config.Running.IS_TEST:
                bol = True
            self.config = config
        except:
            bol=False
            self.config=None
            #logging.debug("error loading config in simple exception handling. Probably fine.")

        tostop= os.environ.get('PYCHARM_HOSTED') == '1'

        tostop = tostop and bol

        self.do_nothing= tostop and not self.never_throw and self.return_succ is None

        return self
    def __exit__(self, exc_type, exc_value, traceback):
        # Code to be executed when exiting the context
        if self.do_nothing:
            return False
        if exc_type is not None:
            # Handle any exceptions raised within the context
            return self.on_exception(exc_type,exc_value,traceback)   # Propagate any exceptions raised within the context

    def on_exception(self, exc_type, exc_value, traceback):
        e=exc_value
        # TmpHook.GetExceptionHook().emit(e)
        if exc_type in self.err_to_ignore and not self.never_throw:
           return False
        logf = logging.debug if self.debug else logging.error
        tmpst = format_traceback_str(exc_type, exc_value, traceback , detailed=self.detailed)
        strng = "# if you see this in your traceback, you should probably inspect the remote traceback as well"
        if strng in tmpst:
            logf(("".join(get_pyro_traceback())))
        if self.err_description:
            logf(self.err_description)
        if self.config is not None and self.config.Running.IS_TEST:
            logf(format_traceback_str(exc_type,exc_value, traceback, detailed=self.detailed))  # just in case
        elif e.__class__ not in default_not_detailed_errors and self.detailed:
            logf(format_traceback_str(exc_type,exc_value, traceback, detailed=self.detailed))
        else:
            logf(str(e))
        if self.always_throw:
           return False
        return True


def simple_exception_handling(err_description=None,return_succ=None,never_throw=False,always_throw=False,debug=False,detailed=True,err_to_ignore=[]):
    def decorated(func):
        def internal(*args,**kwargs):
            no_exception = False
            ret=None
            with SimpleExceptionContext(err_description=err_description,return_succ=return_succ,never_throw=never_throw,always_throw=always_throw,debug=debug,detailed=detailed,err_to_ignore=err_to_ignore):
                ret= func(*args,**kwargs)
                no_exception = True

            if not no_exception and return_succ:
                return return_succ
            return ret

        return internal
    return decorated
