web: python manage.py runserver 0.0.0.0:$PORT --noreload --insecure
worker: cd bestyy && celery -A bestyy worker --loglevel=info
beat: cd bestyy && celery -A bestyy beat --loglevel=info