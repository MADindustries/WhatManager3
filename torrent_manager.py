import django
from django.conf import settings

import WhatManager3.settings as wm_settings


settings.configure(**wm_settings.__dict__)

django.setup()

import torrents.manager.main

torrents.manager.main.run()
