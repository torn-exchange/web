"""
WSGI config for torntrades project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/wsgi/
"""

import os
import newrelic.agent
from dotenv import load_dotenv
from django.core.wsgi import get_wsgi_application

load_dotenv()

newrelic.agent.initialize()

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'torntrades.settings')

application = get_wsgi_application()
application = newrelic.agent.WSGIApplicationWrapper(application)
