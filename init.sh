source ./venv/bin/activate
pip install -r requirements.txt
flask db upgrade;
export FLASK_APP='app.py'
