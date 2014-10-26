import asyncio
import base64
from http.cookies import SimpleCookie
from itertools import count
import logging
import pickle
import re

import aiohttp

from WhatManager3.utils import json_loads
from trackers.rate_limiter import RateLimiter
from trackers.whatcd.models import LoginCache
from trackers.whatcd.settings import WHAT_CD_ROOT


logger = logging.Logger(__name__)

HEADERS = {
    'Accept-Charset': 'utf-8',
    'User-Agent': 'whatapi [karamanolev]'
}

# Taken from Gazelle source, current as of 2014-10-26
RATE_LIMITED_ACTIONS = [
    'tcomments', 'user', 'forum', 'top10', 'browse', 'usersearch', 'requests', 'artist', 'inbox',
    'subscriptions', 'bookmarks', 'announcements', 'notifications', 'request', 'better',
    'similar_artists', 'userhistory', 'votefavorite', 'wiki', 'torrentgroup', 'news_ajax',
    'user_recents', 'collage', 'raw_bbcode']


class RequestException(Exception):
    def __init__(self, message=None, response=None):
        super(Exception, self).__init__(message)
        self.response = response


class LoginException(RequestException):
    def __init__(self, response=None):
        super(LoginException, self).__init__('', response)


class BadIdException(RequestException):
    def __init__(self, response=None):
        super(BadIdException, self).__init__('Bad ID parameter', response)


class RateLimitExceededException(RequestException):
    def __init__(self, response=None):
        super(RateLimitExceededException, self).__init__('Rate limit exceeded', response)


class WhatAPI:
    def __init__(self, username, password):
        self.connector = aiohttp.connector.TCPConnector(share_cookies=True)
        self.authkey = None
        self.passkey = None
        self.username = username
        self.password = password
        self.rate_limiter = RateLimiter(5, 10)
        try:
            login_cache = LoginCache.get()
            self.connector.update_cookies(pickle.loads(base64.b64decode(login_cache.cookies)))
            self.authkey = login_cache.authkey
            self.passkey = login_cache.passkey
        except LoginCache.DoesNotExist:
            pass

    @asyncio.coroutine
    def _login(self):
        """
        Logs in user and gets authkey from server
        """
        login_page = '{0}/login.php'.format(WHAT_CD_ROOT)
        data = {
            'username': self.username,
            'password': self.password,
            'keeplogged': 1,
            'login': 'Login',
        }
        self.connector.cookies = SimpleCookie()
        r = yield from aiohttp.request('get', login_page, connector=self.connector)
        yield from r.text()
        r = yield from aiohttp.request('post', login_page, data=data, headers=HEADERS,
                                       allow_redirects=False, connector=self.connector)
        if r.status == 200:
            raise LoginException(r)
        if r.status != 302:
            raise RequestException('Request exception encountered while trying to log in', r)
        account_info = yield from self.request("index", try_login=False)
        self.authkey = account_info["authkey"]
        self.passkey = account_info["passkey"]
        login_cache = LoginCache(
            cookies=base64.b64encode(pickle.dumps(list(self.connector.cookies.items()))),
            authkey=self.authkey,
            passkey=self.passkey
        )
        LoginCache.set(login_cache)

    @asyncio.coroutine
    def request(self, action, **kwargs):
        """
        Makes an AJAX request at a given action page
        """
        ajax_page = '{0}/ajax.php'.format(WHAT_CD_ROOT)
        params = {'action': action}
        if self.authkey:
            params['auth'] = self.authkey
        params.update(kwargs)
        try_login = params.get('try_login', True)
        if action in RATE_LIMITED_ACTIONS:
            yield from self.rate_limiter.wait_operation()
        r = yield from aiohttp.request('get', ajax_page, params=params, allow_redirects=False,
                                       headers=HEADERS, connector=self.connector)
        response_text = yield from r.text()
        if r.status == 302:
            if not try_login:
                raise LoginException(response=r)
            assert r.headers['Location'] == 'login.php'
            yield from self._login()
            return (yield from self.request(action, **kwargs))
        if r.status != 200:
            raise RequestException(response=r)
        return self.parse_response(json_loads(response_text))

    @asyncio.coroutine
    def request_retry(self, action, retry_limit=5, **kwargs):
        n_retry = 1
        while True:
            try:
                return (yield from self.request(action, **kwargs))
            except LoginException:
                raise
            except RequestException:
                if n_retry <= retry_limit:
                    logger.info('Request failed, retrying in', 2 ** n_retry)
                    yield from asyncio.sleep(2 ** n_retry)
                    n_retry += 1
                else:
                    raise

    def parse_response(self, json_response):
        try:
            if json_response["status"] != "success":
                if json_response['error'] == 'bad id parameter':
                    raise BadIdException(json_response)
                elif json_response['error'] == 'rate limit exceeded':
                    raise RateLimitExceededException(json_response)
                raise RequestException(
                    message=json_response['error'] if 'error' in json_response else json_response,
                    response=json_response)
            return json_response['response']
        except ValueError:
            raise RequestException(response=json_response)

    @asyncio.coroutine
    def get_torrent(self, torrent_id):
        """
        Downloads the torrent at torrent_id using the authkey and passkey
        :param torrent_id: What.CD torrent ID
        :return: A tuple - filename and binary content
        """
        torrent_page = '{0}/torrents.php'.format(WHAT_CD_ROOT)
        params = {'action': 'download', 'id': torrent_id}
        if self.authkey:
            params['authkey'] = self.authkey
            params['torrent_pass'] = self.passkey
        r = yield from aiohttp.request('get', torrent_page, params=params, allow_redirects=False,
                                       connector=self.connector)
        if r.status == 200 and 'application/x-bittorrent' in r.headers['content-type']:
            filename = re.search('filename="(.*)"', r.headers['content-disposition']).group(1)
            return filename, (yield from r.read())
        raise RequestException('Unable to download torrent', response=r)

    @asyncio.coroutine
    def get_browse_results(self, **kwargs):
        results = []
        for page in count(1):
            response = yield from self.request_retry('browse', page=page, **kwargs)
            if response['pages'] > 40:
                raise Exception('More than 20 pages of free torrents. Site-wide freeleech?')
            results.extend(response['results'])
            if response['currentPage'] == response['pages']:
                break
        return results
