import asyncio
import time


class RateLimiter(object):
    def __init__(self, num_requests, num_seconds):
        """
        Creates a rate limiter for N requests max in S seconds (What.CD does 5 requests / 10 secs)
        :param num_requests: Number of request N
        :param num_seconds: Number of seconds S
        """
        self.num_requests = num_requests
        self.num_seconds = num_seconds
        self.request_times = []

    @asyncio.coroutine
    def wait_operation(self):
        now = time.time()
        if len(self.request_times) == self.num_requests:
            last_request = self.request_times.pop(0)
            to_sleep = last_request + self.num_seconds - now
            self.request_times.append(now + to_sleep)
            if to_sleep > 0:
                yield from asyncio.sleep(to_sleep)
        else:
            self.request_times.append(now)
