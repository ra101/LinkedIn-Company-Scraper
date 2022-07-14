import os

from dotenv import load_dotenv
from flask_migrate import Migrate

try:
    from .app import app
    from .models import db
except:
    from app import app
    from models import db


load_dotenv()


app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    "DATABASE_URI", "postgresql://postgres:@localhost:5432/postgres"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
db.init_app(app)
migrate = Migrate(app, db)
app.app_context().push()
