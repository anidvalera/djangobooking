import os
import sys

path = '/home/yourusername/booking2/booking_project/booking'
if path not in sys.path:
    sys.path.append(path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'booking_system.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
