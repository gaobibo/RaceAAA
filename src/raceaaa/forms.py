from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from flask_login import current_user
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, IntegerField, DateField, SelectField, HiddenField, DecimalField, RadioField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Regexp, NumberRange
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from raceaaa import db
from raceaaa.models import User, Member, Event, Race, Checkpoint, Jobtype
from wtforms.fields.html5 import DateField, DateTimeLocalField, TimeField


class RegistrationForm(FlaskForm):
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is taken. Please choose a different one.')


class LoginForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')


class UpdateAccountForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])

    submit = SubmitField('Update')

    def validate_username(self, username):
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('That email is taken. Please choose a different one.')


class MemberUpdateForm(FlaskForm):
    field_fname = StringField('First Name', validators=[DataRequired(), Length(max=100)])
    field_lname = StringField('Last Name', validators=[DataRequired(), Length(max=100)])
    field_bdate = DateField("Date of Birth", format='%Y-%m-%d')
    field_gender = SelectField('Gender', validators=[DataRequired()], choices = [('', '-- please select your gender --'), ('M', 'M'), ('F', 'F')])
    field_phone        = StringField('Phone', validators=[Length(max=50)])
    field_emergcontact = StringField('Emergency Contact', validators=[Length(max=50)])
    field_address      = StringField('Street Address', validators=[Length(max=50)])
    field_city         = StringField('City', validators=[Length(max=50)])
    field_state        = StringField('State', validators=[Length(max=50)])
    field_country      = StringField('Country', validators=[Length(max=50)])
    field_club         = StringField('Club', validators=[Length(max=100)])
    field_picture      = FileField('Update Member Picture', validators=[FileAllowed(['jpg', 'png'])])

    submit = SubmitField('Save')


class MemberNewForm(MemberUpdateForm):
    submit = SubmitField('Join')


class RaceUpdateForm(FlaskForm):
    field_name = StringField('Name', validators = [DataRequired(), Length(max=100)])
    field_distance = DecimalField('Distance', validators = [DataRequired()], places = 1)
    field_starttime = DateTimeLocalField('Start Time', format='%Y-%m-%dT%H:%M')
    field_endtime = DateTimeLocalField('End Time', format='%Y-%m-%dT%H:%M')
    field_capacity = IntegerField('Capacity')
    field_price = IntegerField('Price')
    field_description = TextAreaField('Description')

    submit = SubmitField('Update Race')

    def validate_field_endtime(self, field_endtime):
         if  self.field_starttime.data > field_endtime.data :
             raise ValidationError('The end time cannot be before the start time. Please choose a different time.')


class RaceNewForm(RaceUpdateForm):
    submit = SubmitField('Add Race')


class EventUpdateForm(FlaskForm):
    eventid = HiddenField("")

    name = StringField('Name', validators = [DataRequired(), Length(max=100)])
    field_organization = StringField('Organization', validators=[Length(max=100)])
    logo = FileField('Logo', validators = [FileAllowed(['jpg', 'png'])])
    banner = FileField('Banner', validators = [FileAllowed(['jpg', 'png'])])
    description = TextAreaField('Description')

    startdate    = DateField("Event Start", format='%Y-%m-%d')
    enddate      = DateField("Event End", format='%Y-%m-%d')
    regopendate  = DateField("Registration Open", format='%Y-%m-%d')
    regclosedate = DateField("Registration Close", format='%Y-%m-%d')

    field_address      = StringField('Street Address', validators=[Length(max=50)])
    field_city         = StringField('City', validators=[Length(max=50)])
    field_state        = StringField('State', validators=[Length(max=50)])
    field_country      = StringField('Country', validators=[Length(max=50)])

    submit = SubmitField('Update Event')
    '''
    def validate_name(self, name):
         event = Event.query.filter_by(name = name.data).first()
         if event and (str(event.eventid) != str(self.eventid.data)):
             raise ValidationError('That name is taken. Please choose a different one.')
    '''
    def validate_enddate(self, enddate):
         if  self.startdate.data > enddate.data :
             raise ValidationError('The end date cannot be before the start date. Please choose a different date.')

    def validate_regclosedate(self, regclosedate):
         if  self.regopendate.data > regclosedate.data :
             raise ValidationError('The close date cannot be before the open date. Please choose a different date.')


class EventNewForm(EventUpdateForm):
    submit = SubmitField('Host Event')


###################################################################################################


class RaceRegisterForm(FlaskForm):
    field_raceid = SelectField('Race Name', validators = [DataRequired()])
    field_plannedhour = IntegerField('Planned Finish Time (Hours: 0-838)', validators=[NumberRange(min=0, max=838)], default=0)
    field_plannedminute  = IntegerField('(Minutes: 0-59)', validators=[NumberRange(min=0, max=59)], default=0)
    field_tshirtsize  = SelectField('T-shirt Size', validators=[DataRequired()], choices = [('', '-- please select your size --'), ('XS', 'XS'), ('S', 'S'), ('M', 'M'), ('L', 'L'), ('XL', 'XL')])

    submit = SubmitField('Register')


class JobRequestUpdateForm(FlaskForm):
    field_jobtypeid = SelectField('Type', validators = [DataRequired()])
    field_name = StringField('Name', validators=[DataRequired(), Length(max=100)])
    field_headcount = IntegerField('Headcount', validators=[DataRequired()])
    field_detail = TextAreaField('Detail')

    submit = SubmitField('Update Job')


class JobRequestNewForm(JobRequestUpdateForm):
    submit = SubmitField('Add Job')

