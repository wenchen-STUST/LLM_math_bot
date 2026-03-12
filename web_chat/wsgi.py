"""
WSGI config for web_chat project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_chat.settings')

application = get_wsgi_application()
