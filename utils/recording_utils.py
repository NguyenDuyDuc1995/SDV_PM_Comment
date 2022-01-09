import multiprocessing as mp
from collections.abc import Sequence

import cv2
import numpy as np
from PIL import Image
from mss import mss

from .concurrent.threading_utils import execute_for

# It means when use: <from recording_utils import *>, it will import all in <__all__> variable.
# If this module has many classes or functions, we need to add more code to import
__all__ = ['ScreenRecorder']


def _get_fourcc(fourcc):
    if isinstance(fourcc, int):
        return fourcc
    return cv2.VideoWriter_fourcc(*fourcc)


def _get_bbox(monitor):
    if isinstance(monitor, dict):
        return monitor
    elif isinstance(monitor, Sequence):
        return {
            "left": monitor[0],
            "top": monitor[1],
            "width": monitor[2] - monitor[0],
            "height": monitor[3] - monitor[1],
        }
    return monitor


class _RecordTask:
    def __init__(self,
                 record_file,
                 monitor=0,
                 bbox=None,
                 fps=30,
                 fourcc='DIVX',
                 ):
        print(record_file, monitor, bbox, fps, fourcc)
        self.record_file = record_file
        self.monitor = monitor
        self.bbox = _get_bbox(bbox)
        self.fps = fps
        self.fourcc = _get_fourcc(fourcc)


def _record_worker(record_task_queue: mp.SimpleQueue,
                   start_record_event: mp.Event,
                   started_event: mp.Event):
    started_event.set()
    while True:
        with mss() as sct:
            task = record_task_queue.get()
            screen_bbox = sct.monitors[task.monitor + 1]
            if task.bbox is not None:
                bbox = task.bbox
                bbox['left'] += screen_bbox['left']
                bbox['top'] += screen_bbox['top']
                width, height = task.bbox['width'], task.bbox['height']
            else:
                bbox = screen_bbox
                width, height = screen_bbox['width'], screen_bbox['height']
            bbox['mon'] = task.monitor + 1
            out_video = cv2.VideoWriter(task.record_file,
                                        task.fourcc,
                                        task.fps,
                                        (width, height))
            interval = 1 / task.fps
            start_record_event.wait()
            while start_record_event.is_set():
                with execute_for(interval):
                    img = sct.grab(bbox)
                    img = Image.frombytes('RGB', img.size, img.bgra, 'raw', 'BGRX')
                    img = np.asarray(img, dtype=np.uint8)
                    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                    out_video.write(img)
            out_video.release()

# This class used for recording the screen by making a video.
class ScreenRecorder:
    def __init__(self):
        self._record_task_queue = mp.SimpleQueue()
        self._start_record_event = mp.Event()
        self._subprocess_started_event = mp.Event()
        self._record_process = mp.Process(target=_record_worker,
                                          name='RecordProcess',
                                          args=(self._record_task_queue,
                                                self._start_record_event,
                                                self._subprocess_started_event),
                                          daemon=True)
        self._record_process.start()

    def start_record(self,
                     record_file,
                     monitor=0,
                     bbox=None,
                     fps=30,
                     fourcc='DIVX',
                     ):
        task = _RecordTask(record_file, monitor, bbox, fps, fourcc)
        self._record_task_queue.put(task)
        self._start_record_event.set()

    def stop_record(self):
        self._start_record_event.clear()

    def terminate(self):
        """
        Stop recording and kill the process
        """
        
        self.stop_record()
        self._record_process.terminate()

    def join(self, timeout=None):
        """
        Join the process of recording screen to main thread to close all the process when closing the application
        """
        
        self._record_process.join(timeout)

    def wait_until_subprocess_started(self, timeout=None):
        self._subprocess_started_event.wait(timeout)
