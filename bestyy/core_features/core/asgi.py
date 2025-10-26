"""
ASGI config for bestyy project.
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.core.settings')
application = get_asgi_application()