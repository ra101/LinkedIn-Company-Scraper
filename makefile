server:
	gunicorn wsgi:application

celery:
	celery --app app.celery worker --loglevel=debug

flower:
	celery --app app.celery flower
