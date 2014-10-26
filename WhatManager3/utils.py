from datetime import datetime
import html
import os
import ujson

from django.db import close_old_connections
import pytz


def json_loads(value):
    return ujson.loads(value)


def json_dumps(value):
    return ujson.dumps(value)


def html_unescape(data):
    return html.unescape(data)


def parse_db_datetime(value):
    return datetime.strptime(value, '%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.UTC)


def prune_connections():
    close_old_connections()


def db_func(func):
    def inner(*args, **kwargs):
        # prune_connections()
        return func(*args, **kwargs)

    return inner


def load_fixture(filename):
    path = os.path.dirname(os.path.realpath(__file__))
    path = os.path.join(path, '..', 'fixtures', filename)
    with open(path, 'rb') as f:
        data = f.read()
    return data
