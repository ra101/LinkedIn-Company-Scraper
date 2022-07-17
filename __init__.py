import os, sys

from dotenv import load_dotenv
from flask_migrate import Migrate

sys.path.append(os.getcwd())
load_dotenv()

from app import app
from models import db


app.config.update(
    SQLALCHEMY_TRACK_MODIFICATIONS=True,
    SQLALCHEMY_DATABASE_URI=os.getenv(
        "DATABASE_URI", "postgresql://postgres:@localhost:5432/postgres"
    ),
    CELERY_BROKER_URL=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379"),
    CELERY_RESULT_BACKEND=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379"),
)
db.init_app(app)
migrate = Migrate(app, db)
app.app_context().push()
