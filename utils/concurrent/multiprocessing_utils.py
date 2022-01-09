import multiprocessing as mp
import queue
import threading
from collections import UserDict
from concurrent.futures import as_completed, wait, Future

from .threading_utils import TerminateableThread, ThreadTerminatedError

__all__ = ['Subprocess', 'SubprocessExecutor',
           'as_completed', 'wait', 'Future']


class VariableArg:
    def __init__(self, variable_name):
        self.variable_name = variable_name


class _Task(object):
    def __init__(self, work_id):
        self.work_id = work_id


class _InitVariableTask(_Task):
    def __init__(self,
                 work_id,
                 variable_name,
                 variable_value=None,
                 variable_class=None,
                 init_args=(),
                 init_kwargs={}):
        super(_InitVariableTask, self).__init__(work_id)
        self.variable_name = variable_name
        self.variable_value = variable_value
        self.variable_class = variable_class
        self.init_args = init_args
        self.init_kwargs = init_kwargs

    def __call__(self):
        if self.variable_class is not None:
            return self.variable_class(*self.init_args, **self.init_kwargs)
        else:
            return self.variable_value


class _GetVariableTask(_Task):
    def __init__(self, work_id, variable_name):
        super(_GetVariableTask, self).__init__(work_id)
        self.variable_name = variable_name


class _DeleteVariableTask(_Task):
    def __init__(self, work_id, variable_name):
        super(_DeleteVariableTask, self).__init__(work_id)
        self.variable_name = variable_name


class _CallTask(_Task):
    def __init__(self, work_id, fn, args=(), kwargs={}):
        super(_CallTask, self).__init__(work_id)
        self.fn = fn
        self.args = list(args)
        self.kwargs = kwargs


class _WorkItem(object):
    def __init__(self, future: Future, task: _Task):
        self.future = future
        self.task = task

    @property
    def id(self):
        return self.task.work_id


class _ResultItem(object):
    def __init__(self, work_id, exception=None, result=None):
        self.work_id = work_id
        self.exception = exception
        self.result = result


class _VariableDict(UserDict):
    def __getitem__(self, item):
        try:
            return super(_VariableDict, self).__getitem__(item)
        except KeyError:
            raise NameError(f'variable {item} is not defined')


def _task_execution_worker(variable_dict,
                           task_queue,
                           result_queue):
    while True:
        task = task_queue.get()
        result_item = _ResultItem(task.work_id)
        try:
            if isinstance(task, _CallTask):
                for i, v in enumerate(task.args):
                    if isinstance(v, VariableArg):
                        task.args[i] = variable_dict[v.variable_name]
                for k, v in task.kwargs.items():
                    if isinstance(v, VariableArg):
                        task.kwargs[k] = variable_dict[v.variable_name]
                result_item.result = task.fn(*task.args, **task.kwargs)
            elif isinstance(task, _InitVariableTask):
                variable_dict[task.variable_name] = task()
            elif isinstance(task, _GetVariableTask):
                result_item.result = variable_dict[task.variable_name]
            elif isinstance(task, _DeleteVariableTask):
                variable_dict.pop(task.variable_name)
        except ThreadTerminatedError as e:
            result_item.exception = e
            raise e
        except Exception as e:
            result_item.exception = e
        finally:
            if result_item.work_id is not None:
                result_queue.put(result_item)


class Subprocess(mp.Process):
    def __init__(self,
                 task_queue: mp.SimpleQueue = None,
                 result_queue: mp.SimpleQueue = None,
                 group=None, name=None, *, max_workers=1, daemon=None):
        super(Subprocess, self).__init__(group=group, name=name, daemon=daemon)
        self._task_queue = task_queue if task_queue is not None else mp.SimpleQueue()
        self._result_queue = result_queue if result_queue is not None else mp.SimpleQueue()
        self.max_workers = max_workers

        self._variables = _VariableDict()
        self._task_executor_threads = []

    def run(self):
        self._task_executor_threads = [
            TerminateableThread(target=_task_execution_worker,
                                args=(self._variables,
                                      self._task_queue,
                                      self._result_queue),
                                raise_exception=True,
                                daemon=True)
            for _ in range(self.max_workers)
        ]
        [thread.start() for thread in self._task_executor_threads]
        [thread.join() for thread in self._task_executor_threads]

    def terminate(self):
        super(Subprocess, self).terminate()
        [thread.terminate() for thread in self._task_executor_threads]

    @staticmethod
    def variable_arg(variable_name):
        return VariableArg(variable_name)

    def init_variable(self, variable_name, variable_value=None, variable_class=None, init_args=(), init_kwargs={}):
        self._task_queue.put(_InitVariableTask(None,
                                               variable_name,
                                               variable_value,
                                               variable_class,
                                               init_args,
                                               init_kwargs))

    def get_variable(self, variable_name):
        self._task_queue.put(_GetVariableTask(None,
                                              variable_name))

    def delete_variable(self, variable_name):
        self._task_queue.put(_DeleteVariableTask(None,
                                                 variable_name))

    def call(self, fn, args=(), kwargs={}):
        self._task_queue.put(_CallTask(None,
                                       fn,
                                       args,
                                       kwargs))


def _add_call_item_to_queue(pending_work_items,
                            work_ids_queue,
                            task_queue):
    while True:
        if task_queue.full():
            return
        try:
            work_id = work_ids_queue.get(block=False)
        except queue.Empty:
            return
        else:
            work_item = pending_work_items[work_id]

            if work_item.future.set_running_or_notify_cancel():
                task_queue.put(work_item.task, block=True)
            else:
                del pending_work_items[work_id]
                continue


def _work_management_worker(pending_work_items,
                            work_ids_queue,
                            task_queue):
    while True:
        work_id = work_ids_queue.get()
        task_queue.put(pending_work_items[work_id].task)


def _result_management_worker(pending_work_items,
                              result_queue: mp.SimpleQueue):
    # result_reader = result_queue._reader
    while True:
        # _add_call_item_to_queue(pending_work_items, work_ids_queue, task_queue)

        # ready = mp.connection.wait([result_reader])
        # if result_reader in ready:
        #     result_item = result_reader.recv()
        result_item = result_queue.get()

        work_item = pending_work_items.pop(result_item.work_id, None)
        # work_item can be None if another process terminated (see above)
        if work_item is not None:
            if result_item.exception:
                work_item.future.set_exception(result_item.exception)
            else:
                work_item.future.set_result(result_item.result)
            del work_item
        del result_item


class SubprocessExecutor:
    def __init__(self, group=None, name=None, *, max_workers=1, daemon=None):
        self._pending_works = {}
        self._work_ids_queue = queue.Queue()
        self._work_queue_count = 0

        self._task_queue = mp.SimpleQueue()
        self._result_queue = mp.SimpleQueue()

        self._proc = Subprocess(self._task_queue,
                                self._result_queue,
                                group, name,
                                max_workers=max_workers,
                                daemon=daemon)
        self._result_manager_thread = None
        self._work_manager_thread = None

    @property
    def max_workers(self):
        return self._proc.max_workers

    def _wakeup_manager_threads(self):
        if self._work_manager_thread is None:
            self._work_manager_thread = threading.Thread(target=_work_management_worker,
                                                         args=(self._pending_works,
                                                               self._work_ids_queue,
                                                               self._task_queue,
                                                               ),
                                                         daemon=True)
            self._work_manager_thread.start()
        if self._result_manager_thread is None:
            self._result_manager_thread = threading.Thread(target=_result_management_worker,
                                                           args=(self._pending_works,
                                                                 # self._work_ids_queue,
                                                                 # self._task_queue,
                                                                 self._result_queue,
                                                                 ),
                                                           daemon=True)
            self._result_manager_thread.start()

    def start(self):
        self._proc.start()

    def terminate(self):
        self._proc.terminate()

    def join(self, timeout=None):
        self._proc.join(timeout)

    @staticmethod
    def variable_arg(variable_name):
        return VariableArg(variable_name)

    def init_variable(self, variable_name, variable_value=None, variable_class=None, init_args=(), init_kwargs={}):
        f = Future()
        w = _WorkItem(f, _InitVariableTask(self._work_queue_count,
                                           variable_name,
                                           variable_value,
                                           variable_class,
                                           init_args,
                                           init_kwargs))
        self._pending_works[w.id] = w
        self._work_ids_queue.put(w.id)
        self._work_queue_count += 1
        self._wakeup_manager_threads()
        return f

    def get_variable(self, variable_name):
        f = Future()
        w = _WorkItem(f, _GetVariableTask(self._work_queue_count,
                                          variable_name))
        self._pending_works[w.id] = w
        self._work_ids_queue.put(w.id)
        self._work_queue_count += 1
        self._wakeup_manager_threads()
        return f

    def delete_variable(self, variable_name):
        f = Future()
        w = _WorkItem(f, _DeleteVariableTask(self._work_queue_count,
                                             variable_name))
        self._pending_works[w.id] = w
        self._work_ids_queue.put(w.id)
        self._work_queue_count += 1
        self._wakeup_manager_threads()
        return f

    def call(self, target, args=(), kwargs={}):
        f = Future()
        w = _WorkItem(f, _CallTask(self._work_queue_count,
                                   target,
                                   args,
                                   kwargs))
        self._pending_works[w.id] = w
        self._work_ids_queue.put(w.id)
        self._work_queue_count += 1
        self._wakeup_manager_threads()
        return f
