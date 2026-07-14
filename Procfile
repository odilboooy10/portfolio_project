release: sh -c "cd core && python manage.py migrate --settings=config.settings.production && python manage.py collectstatic --noinput --settings=config.settings.production"
web: gunicorn config.wsgi:application --chdir core --bind 0.0.0.0:$PORT --workers 3 --timeout 120
worker: celery -A config worker --loglevel=info --workdir core
