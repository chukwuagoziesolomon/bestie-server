#!/bin/bash
exec gunicorn scribbleintimeai.wsgi:application --bind 0.0.0.0:$PORT
