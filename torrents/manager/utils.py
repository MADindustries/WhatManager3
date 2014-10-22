import time


class Timer(object):
    def __init__(self, logger, op):
        self.logger = logger
        self.op = op

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end = time.time()
        self.duration = self.end - self.start
        self.logger.info('{0} took {1}'.format(self.op, self.duration))
