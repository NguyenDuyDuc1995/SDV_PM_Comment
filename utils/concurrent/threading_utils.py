import ctypes
import inspect
import threading
import time

__all__ = ['sleep', 'timeit', 'execute_for',
           'TerminateableThread', 'ThreadTerminatedError']


def sleep(timeout):
    if timeout > 0:
        event = threading.Event()
        return event.wait(timeout)


class timeit:
    def __init__(self):
        self.start: float = None
        self.end: float = None
        self.elapsed_time: float = None

    def __enter__(self):
        self.start = time.time()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end = time.time()
        self.elapsed_time = self.end - self.start


class execute_for:
    def __init__(self, expected_time):
        self.start: float = None
        self.end: float = None
        self.elapsed_time: float = expected_time

    def __enter__(self):
        self.start = time.time()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end = time.time()
        expected_time = self.end - self.start
        sleep(self.elapsed_time - expected_time)


def _async_raise(tid, exception_type):
    """Raises an exception in the threads with id tid"""
    if not inspect.isclass(exception_type):
        raise TypeError("Only types can be raised (not instances)")
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid),
                                                     ctypes.py_object(exception_type))
    if res == 0:
        raise ValueError(f"invalid thread id {res}")
    elif res != 1:
        # "if it returns a number greater than one, you're in trouble,
        # and you should call it again with exc=NULL to revert the effect"
        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), None)
        raise SystemError("PyThreadState_SetAsyncExc failed")


class ThreadTerminatedError(threading.ThreadError):
    pass


class TerminateableThread(threading.Thread):

    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, *, raise_exception=True, daemon=None):
        super(TerminateableThread, self).__init__(group, target, name, args, kwargs, daemon=daemon)
        self._terminate_event = threading.Event()
        self._raise_exception = raise_exception
        self._thread_id = None

    def start(self):
        super(TerminateableThread, self).start()
        self.thread_id()

    def thread_id(self):
        if not self.is_alive():
            raise threading.ThreadError("the thread is not active")
        # do we have it cached?
        if self._thread_id is not None:
            return self._thread_id
        # no, look for it in the _active dict
        for tid, tobj in threading._active.items():
            if tobj is self:
                self._thread_id = tid
                return tid
        raise AssertionError("unable to determine the thread's id")

    def raise_exception(self, exception_type):
        _async_raise(self.thread_id(), exception_type)

    def terminate(self):
        self._terminate_event.set()
        if self._raise_exception and self.is_alive():
            self.raise_exception(ThreadTerminatedError)

    def is_terminated(self):
        return self._terminate_event.is_set()
