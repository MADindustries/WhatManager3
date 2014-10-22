from datetime import datetime

from django.test.testcases import TestCase
import pytz

from WhatManager3.utils import parse_db_datetime, html_unescape, json_loads, json_dumps


class UtilsTestCase(TestCase):
    def test_html_unescape(self):
        self.assertEqual(html_unescape('hel&amp;lo&lt;'), 'hel&lo<')

    def test_parse_db_datetime(self):
        self.assertEqual(parse_db_datetime('2014-08-04 23:22:59'),
                         datetime(2014, 8, 4, 23, 22, 59, tzinfo=pytz.UTC))

    def test_json(self):
        text = '{"hi":"world"}'
        self.assertEqual(text, json_dumps(json_loads(text)))
