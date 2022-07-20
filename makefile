server:
	gunicorn wsgi:application

celery:
	celery --app app.celery worker --loglevel=debug

flower:
	celery --app app.celery flower

supervisor-start:
	sudo service supervisor restart ;\
	sudo supervisord -c ./supervisor.conf ;\
	supervisorctl -c ./supervisor.conf start all

supervisor-stop:
	supervisorctl -c ./supervisor.conf stop all ;\
	sudo service supervisor stop

supervisor-status:
	supervisorctl -c ./supervisor.conf status
