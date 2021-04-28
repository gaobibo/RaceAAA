from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager

mysql_connect_host = 'localhost'
mysql_connect_user = 'bgao'
mysql_connect_password = 'Loyola1234'
mysql_connect_database = 'raceaaa'

app = Flask(__name__)

app.config['SECRET_KEY'] = '5791628bb0b13ce0c676dfde280ba245'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://' + mysql_connect_user + ':' + mysql_connect_password + '@' + mysql_connect_host + '/' + mysql_connect_database

app.config['CLOUD_STORAGE_USED'] = ''#'GOOGLE'
app.config['CLOUD_STORAGE_URL']  = ''#'https://storage.googleapis.com/bkt-race-aaa'
app.config['CLOUD_STORAGE_NAME'] = ''#'bkt-race-aaa'

db = SQLAlchemy(app)

bcrypt = Bcrypt(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

from raceaaa import routes
from raceaaa import models

models.db.create_all()
