source ./venv/bin/activate
pip install -r requirements.txt
export FLASK_APP='app.py'
flask db upgrade;
