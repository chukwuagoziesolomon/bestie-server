"""
WSGI config for bestyy project.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.core.settings')
application = get_wsgi_application()