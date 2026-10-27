web: python manage.py migrate && gunicorn exam_guard.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120
