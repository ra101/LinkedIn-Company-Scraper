server:
	gunicorn wsgi:application

celery:
	celery --app celery_queue.celery worker --loglevel=info
