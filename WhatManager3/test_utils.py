import os.path
from unittest.mock import patch

from django.test import TestCase as DjangoTestCase


def load_fixture(filename):
    path = os.path.dirname(os.path.realpath(__file__))
    path = os.path.join(path, '..', 'fixtures', filename)
    with open(path, 'rb') as f:
        data = f.read()
    return data


class TestCase(DjangoTestCase):
    def setUp(self):
        self.assertIsNone(getattr(self, 'close_old_connections_patcher', None))
        self.close_old_connections_patcher = patch('django.db.close_old_connections', lambda: None)
        self.close_old_connections_patcher.start()
        super(DjangoTestCase, self).setUp()

    def tearDown(self):
        self.close_old_connections_patcher.stop()
        self.close_old_connections_patcher = None
        super(DjangoTestCase, self).setUp()
