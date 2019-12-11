"""pedlarweb entry point."""
from flask import Flask

# pylint: disable=wrong-import-position

server = Flask(__name__)


# Load extensions here for now
from flask_bcrypt import Bcrypt
bcrypt = Bcrypt(server)

from flask_login import LoginManager
login_manager = LoginManager(server)
login_manager.login_view = "login"

from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy(server)




