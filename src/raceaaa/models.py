from raceaaa import db, login_manager
from flask_login import UserMixin
from datetime import datetime


db.Model.metadata.reflect(db.engine)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.image_file}')"


class Member(db.Model):
    __table__ = db.Model.metadata.tables['members']


class Event(db.Model):
    __table__ = db.Model.metadata.tables['events']


class Race(db.Model):
    __table__ = db.Model.metadata.tables['race']


class Checkpoint(db.Model):
    __table__ = db.Model.metadata.tables['checkpoint']


class Jobtype(db.Model):
    __table__ = db.Model.metadata.tables['jobtype']


class Jobrequest(db.Model):
    __table__ = db.Model.metadata.tables['jobrequest']


class Apply(db.Model):
    __table__ = db.Model.metadata.tables['apply']


class Participate(db.Model):
    __table__ = db.Model.metadata.tables['participate']


class Timing(db.Model):
    __table__ = db.Model.metadata.tables['timing']

    

  
