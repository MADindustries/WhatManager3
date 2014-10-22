import asyncio
import traceback

import tornado.web

from WhatManager3.utils import json_dumps


class JsonWhatManagerRequestHandler(tornado.web.RequestHandler):
    @asyncio.coroutine
    def get_json(self, *args, **kwargs):
        raise tornado.web.HTTPError(405)

    @tornado.web.asynchronous
    def get(self, *args, **kwargs):
        asyncio.async(self.handle_coro(self.get_json, *args, **kwargs))

    @asyncio.coroutine
    def post_json(self, *args, **kwargs):
        raise tornado.web.HTTPError(405)

    @tornado.web.asynchronous
    def post(self, *args, **kwargs):
        asyncio.async(self.handle_coro(self.post_json, *args, **kwargs))

    @asyncio.coroutine
    def handle_coro(self, method, *args, **kwargs):
        try:
            response = yield from method(*args, **kwargs)
        except tornado.web.HTTPError as e:
            self._handle_request_exception(e)
            return
        except Exception as e:
            tb = traceback.format_exc()
            response = {
                'success': False,
                'error_code': 'exception',
                'error': '{0}({1})'.format(type(e).__name__, str(e)),
                'traceback': tb,
            }
        self.set_status(200)
        self.set_header('Content-Type', 'application/json')
        self.write(json_dumps(response).encode('utf-8'))
        self.finish()
