web: cd bestyy && daphne -b 0.0.0.0 -p $PORT bestyy.asgi:application
worker: cd bestyy && celery -A bestyy worker --loglevel=info
beat: cd bestyy && celery -A bestyy beat --loglevel=info