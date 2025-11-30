# main.py
from flask import Flask
from database import db
import controllers
import os

app = Flask(__name__)

# SQLite DB path stored in a relative 'database' folder (portable)
basedir = os.path.abspath(os.path.dirname(__file__))
db_file = os.path.join(basedir, "database", "data.db")
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_file}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get("HMS_SECRET_KEY", "replace_this_secret")

# init db (pattern same as your sample)
db.init_app(app)
app.app_context().push()

# register controllers (you'll create these in controllers/)
from controllers.control_auth import *
# from controllers.control_user import *
# from controllers.control_admin import *
# from controllers.control_prof import *
# comment them in until you create the files to avoid import errors

if __name__ == '__main__':
    # dev server; use debug=True while developing
    app.run(debug=True, port=5000)
