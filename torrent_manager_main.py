import django
from django.conf import settings

settings.configure(DATABASES={
    'default': {
        'ENGINE': 'mysql.connector.django',
        'NAME': 'what_manager3',
        'USER': 'root',
        'PASSWORD': '',
        'HOST': '127.0.0.1',
        'CONN_MAX_AGE': 10
    },
})

django.setup()

import torrent_manager.main

torrent_manager.main.main()
