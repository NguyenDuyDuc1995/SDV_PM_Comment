import time

# It means when use: <from fps_tracker import *>, it will import all in <__all__> variable.
# If this module has many classes or functions, we need to add more code to import
__all__ = ['FPSTracker']


class FPSTracker:
    def __init__(self, sigma=30):
        """
        Initalize
        """

        self.sigma = sigma
        self.count = 0
        self.average_elapsed_time = None
        self._start = self._end = self._last_elapsed_time = None

    # Using in <With> block to record time for a code block
    def __enter__(self):
        self._start = time.time()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._end = time.time()
        self.update(self._end - self._start)

    # Using to record time from <tick> to <tock>
    def tick(self):
        self._start = time.time()

    def tock(self):
        self._end = time.time()
        self.update(self._end - self._start)

    # Calculating average time, if <count number> > 30, avg Time is of the last 30 times
    def update(self, elapsed_time):
        self._last_elapsed_time = elapsed_time
        self.count = min(self.count + 1, self.sigma)
        if self.count == 1:
            self.average_elapsed_time = self._last_elapsed_time
        else:
            self.average_elapsed_time = \
                ((self.count - 1) * self.average_elapsed_time + self._last_elapsed_time) / self.count

    @property   # Create properties for the class
    def fps(self):
        # if self.average_elapsed_time != None:
        #     result = self.average_elapsed_time
        # else:
        #     result = float('nan')
        
        # # Convert from time to frequency
        # result = 1. / result            
        # return result

        return 1. / self.average_elapsed_time if self.average_elapsed_time is not None else float('nan')

