import os
import psutil
import threading
import secrets
from PIL import Image
from flask import render_template, url_for, flash, redirect, request, abort
from raceaaa import app, db, bcrypt, mysql_connect_host, mysql_connect_database, mysql_connect_user, mysql_connect_password
from raceaaa.forms import RegistrationForm, LoginForm, UpdateAccountForm, EventNewForm, EventUpdateForm, MemberUpdateForm, MemberNewForm, RaceUpdateForm, RaceNewForm, RaceRegisterForm, JobRequestUpdateForm, JobRequestNewForm
from raceaaa.models import User, Member, Event, Race, Checkpoint, Participate, Jobrequest, Jobtype, Apply
from flask_login import login_user, current_user, logout_user, login_required
from datetime import datetime, date
from flask import jsonify


def debug():
    pid = os.getpid()
    num = psutil.Process(pid).num_threads()
    tid = threading.get_native_id()
    debug = f'DEBUG {int(request.is_multiprocess)}.{int(request.is_multithread)}.{pid}.{num}.{tid}'
    return debug


@app.route("/")
@app.route("/home")
def home():
    results = Event.query.filter(Event.enddate >= date.today()).order_by(Event.startdate).limit(10).all()
    first = (results[0] if results else None)
    return render_template('home.html', debug=debug(), outString = results, first = first)


@app.route("/about")
def about():
    return render_template('about.html', title='About')


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))


def save_picture(form_picture, save_path):
    # New picture name and path
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, save_path, picture_fn)

    # Adjust picture path if cloud storage is used
    if app.config['CLOUD_STORAGE_USED'] == 'GOOGLE':
        picture_path = os.path.join('/tmp', picture_fn)

    i = Image.open(form_picture)

    # Thumbnail the image (preserve the original aspect ratio by default)
    output_size = (125, 125)
    i.thumbnail(output_size)

    # Save resized image
    i.save(picture_path)

    # Upload to cloud storage if cloud storage is used
    if app.config['CLOUD_STORAGE_USED'] == 'GOOGLE':
        from google.cloud import storage
        storage_client = storage.Client()
        bucket = storage_client.get_bucket(app.config['CLOUD_STORAGE_NAME'])
        blob = bucket.blob(save_path + picture_fn)
        blob.upload_from_filename(picture_path)

    return picture_fn


def crop_picture(form_picture, save_path, new_width, new_height):
    # New picture name and path
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, save_path, picture_fn)

    # Adjust picture path if cloud storage is used
    if app.config['CLOUD_STORAGE_USED'] == 'GOOGLE':
        picture_path = os.path.join('/tmp', picture_fn)

    im = Image.open(form_picture)
    width, height = im.size

    # Resize the image with the original aspect ratio
    tmp_width = new_width
    tmp_height = round(new_width / width * height)
    im = im.resize((tmp_width, tmp_height))

    # Calculate the central coordination
    left = round((tmp_width - new_width) / 2)
    top = round((tmp_height - new_height) / 2)
    right = left + new_width
    bottom = top + new_height

    # Crop the image
    im = im.crop((left, top, right, bottom))

    # Save the cropped image
    im.save(picture_path)

    # Upload to cloud storage if cloud storage is used
    if app.config['CLOUD_STORAGE_USED'] == 'GOOGLE':
        from google.cloud import storage
        storage_client = storage.Client()
        bucket = storage_client.get_bucket(app.config['CLOUD_STORAGE_NAME'])
        blob = bucket.blob(save_path + picture_fn)
        blob.upload_from_filename(picture_path)

    return picture_fn


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    return render_template('account.html', title='Account', form=form)


@app.route("/member", methods=['GET', 'POST'])
@login_required
def member():
    current_member = Member.query.filter_by(userid = current_user.id).first()
    if current_member:
        form = MemberUpdateForm()
        current_member_image = app.config['CLOUD_STORAGE_URL'] + url_for('static', filename='profile_pics/' + current_member.pic)
        today = date.today()
        current_member_age = today.year - current_member.bdate.year - ((today.month, today.day) < (current_member.bdate.month, current_member.bdate.day))
    else:
        form = MemberNewForm()
        current_member_image = app.config['CLOUD_STORAGE_URL'] + url_for('static', filename='profile_pics/' + "member_pic_default.jpg")
        current_member_age = ''

    if form.validate_on_submit():
        if form.field_picture.data:
            new_picture = save_picture(form.field_picture.data, "static/profile_pics/")
        else:
            new_picture = None
        if current_member:
            current_member.fname = form.field_fname.data
            current_member.lname = form.field_lname.data
            current_member.gender = form.field_gender.data
            current_member.bdate = form.field_bdate.data
            current_member.phone = form.field_phone.data
            current_member.emergcontact = form.field_emergcontact.data
            current_member.address = form.field_address.data
            current_member.city = form.field_city.data
            current_member.state = form.field_state.data
            current_member.country = form.field_country.data
            current_member.club = form.field_club.data
            if new_picture:
                current_member.pic = new_picture
        else:
            new_member = Member(userid = current_user.id,
                fname = form.field_fname.data,
                lname = form.field_lname.data,
                gender = form.field_gender.data,
                bdate = form.field_bdate.data,
                phone = form.field_phone.data,
                emergcontact = form.field_emergcontact.data,
                address = form.field_address.data,
                city = form.field_city.data,
                state = form.field_state.data,
                country = form.field_country.data,
                club = form.field_club.data)
            if new_picture:
                new_member.pic = new_picture
            db.session.add(new_member)
        db.session.commit()
        flash('Your member info has been saved!', 'success')
        return redirect(url_for('home'))
    elif request.method == 'GET':
        if current_member:
            form.field_fname.data = current_member.fname
            form.field_lname.data = current_member.lname
            form.field_gender.data = current_member.gender
            form.field_bdate.data = current_member.bdate
            form.field_phone.data = current_member.phone
            form.field_emergcontact.data = current_member.emergcontact
            form.field_address.data = current_member.address
            form.field_city.data = current_member.city
            form.field_state.data = current_member.state
            form.field_country.data = current_member.country
            form.field_club.data = current_member.club
    return render_template('member.html', title='Member', member=current_member, age=current_member_age, image_file=current_member_image, form=form)


@app.route("/event/<eventid>")
def event(eventid):
    event = Event.query.get_or_404(eventid)
    race_list = Race.query.filter_by(eventid = eventid)

    race_director = False
    if current_user.is_authenticated:
        member = Member.query.filter_by(userid = current_user.id).first()
        if member:
            if member.memberid == event.memberid:
                race_director = True
    
    current_event_logo   = app.config['CLOUD_STORAGE_URL'] + url_for('static', filename='event_pics/' + event.logo)
    current_event_banner = app.config['CLOUD_STORAGE_URL'] + url_for('static', filename='event_pics/' + event.banner)
    return render_template('event_detail.html', title=event.name, event=event, races=race_list, logo_file=current_event_logo, banner_file=current_event_banner, race_director=race_director)


@app.route("/event/new", methods=['GET', 'POST'])
@login_required
def new_event():
    member = Member.query.filter_by(userid = current_user.id).first()

    if member is None:
        flash('You have to become a member! Click Membership in My Account', 'danger')
        return redirect(url_for('home'))
    
    default_event_logo   = app.config['CLOUD_STORAGE_URL'] + url_for('static', filename='event_pics/' + "event_logo_default.jpg")
    default_event_banner = app.config['CLOUD_STORAGE_URL'] + url_for('static', filename='event_pics/' + "event_banner_default.jpg")
    form = EventNewForm()
    if form.validate_on_submit():
        event = Event(name = form.name.data, description = form.description.data, 
            startdate = form.startdate.data, enddate = form.enddate.data, 
            regopendate = form.regopendate.data, regclosedate = form.regclosedate.data, 
            memberid=member.memberid,
            address = form.field_address.data,
            city = form.field_city.data,
            state = form.field_state.data,
            country = form.field_country.data,
            organization = form.field_organization.data)
        if form.logo.data:
            event.logo = save_picture(form.logo.data, 'static/event_pics/')
        if form.banner.data:
            event.banner = crop_picture(form.banner.data, 'static/event_pics/', 1100, 300)
            event.xbanner = crop_picture(form.banner.data, 'static/event_pics/', 1100, 500)
        db.session.add(event)
        db.session.commit()
        flash('You have hosted a new event!', 'success')
        return redirect(url_for('home'))
    elif request.method == 'GET':
        form.regopendate.data = date.today()
        form.regclosedate.data = date.today()
        form.startdate.data = date.today()
        form.enddate.data = date.today()
    return render_template('create_event.html', title='Host Event', event=None, form=form, logo_file=default_event_logo, banner_file=default_event_banner, legend='Event Info')


@app.route("/event/<eventid>/update", methods=['GET', 'POST'])
@login_required
def update_event(eventid):
    event = Event.query.get_or_404(eventid)
    member = Member.query.filter_by(userid = current_user.id).first()

    if member is None or member.memberid != event.memberid:
        flash('You are not allowed to update!', 'danger')
        return redirect(url_for('event', eventid=eventid))
    
    current_event_logo   = app.config['CLOUD_STORAGE_URL'] + url_for('static', filename='event_pics/' + event.logo)
    current_event_banner = app.config['CLOUD_STORAGE_URL'] + url_for('static', filename='event_pics/' + event.banner)
    form = EventUpdateForm()
    if form.validate_on_submit():
        if form.logo.data:
            event.logo = save_picture(form.logo.data, 'static/event_pics/')
        if form.banner.data:
            event.banner = crop_picture(form.banner.data, 'static/event_pics/', 1100, 300)
            event.xbanner = crop_picture(form.banner.data, 'static/event_pics/', 1100, 500)
        event.name = form.name.data
        event.description = form.description.data
        event.startdate = form.startdate.data
        event.enddate = form.enddate.data
        event.regopendate = form.regopendate.data
        event.regclosedate = form.regclosedate.data
        event.address = form.field_address.data
        event.city = form.field_city.data
        event.state = form.field_state.data
        event.country = form.field_country.data
        event.organization = form.field_organization.data
        db.session.commit()
        flash('Your event has been updated!', 'success')
        return redirect(url_for('event', eventid=eventid))
    elif request.method == 'GET':
        form.eventid.data = event.eventid
        form.name.data = event.name
        form.description.data = event.description
        form.startdate.data = event.startdate
        form.enddate.data = event.enddate
        form.regopendate.data = event.regopendate
        form.regclosedate.data = event.regclosedate
        form.field_address.data = event.address
        form.field_city.data = event.city
        form.field_state.data = event.state
        form.field_country.data = event.country
        form.field_organization.data = event.organization
    return render_template('create_event.html', title='Update Event', event=event, form=form, logo_file=current_event_logo, banner_file=current_event_banner, legend='Event Info')


@app.route("/event/<eventid>/delete", methods=['POST'])
@login_required
def delete_event(eventid):
    event = Event.query.get_or_404(eventid)
    member = Member.query.filter_by(userid = current_user.id).first()

    if member is None or member.memberid != event.memberid:
        flash('You are not allowed to delete!', 'danger')
        return redirect(url_for('event', eventid=eventid))

    try :
        db.session.delete(event)
        db.session.commit()
        flash('The event has been deleted!', 'success')
    except :
        flash('The event cannot be deleted!', 'danger')
    return redirect(url_for('home'))


@app.route("/myevents")
@login_required
def myevents():
    member = Member.query.filter_by(userid = current_user.id).first()
    
    if member is None:
        flash('You have to become a member! Click Membership in My Account', 'danger')
        return redirect(url_for('home'))
    
    member_participated_events = Participate.query.join(Race, Participate.raceid == Race.raceid) \
        .join(Event, Event.eventid == Race.eventid) \
        .add_columns(Event.eventid, Event.name, Event.startdate, Event.state, Event.country, Race.name.label('rname'), Participate.finishedtime, Participate.memberid) \
        .filter(Participate.memberid == member.memberid) \
        .order_by(Event.startdate)
    
    member_volunteered_events = Apply.query.join(Jobrequest, Apply.jobrequestid == Jobrequest.jobrequestid) \
        .join(Event, Event.eventid == Jobrequest.eventid) \
        .add_columns(Event.eventid, Event.name, Event.startdate, Event.state, Event.country, Jobrequest.name.label('jname'), Apply.appliedtime, Apply.memberid) \
        .filter(Apply.memberid == member.memberid) \
        .order_by(Event.startdate)

    member_hosted_eventids = Event.query.with_entities(Event.eventid).filter(Event.memberid == member.memberid).subquery()
    member_hosted_events = Event.query.outerjoin(Race, Event.eventid == Race.eventid) \
        .add_columns(Event.eventid, Event.name, Event.startdate, Event.state, Event.country, Race.name.label('rname'), Race.raceid, Event.memberid) \
        .filter(Event.eventid.in_(member_hosted_eventids)).order_by(Event.startdate)
    
    member_image = app.config['CLOUD_STORAGE_URL'] + url_for('static', filename='profile_pics/' + member.pic)
    today = date.today()
    member_age = today.year - member.bdate.year - ((today.month, today.day) < (member.bdate.month, member.bdate.day))
    return render_template('my_event.html', image_file = member_image, member = member, age = member_age, participated_events = member_participated_events, volunteered_events = member_volunteered_events, hosted_events = member_hosted_events)


@app.route("/runner/<memberid>")
def runner(memberid):
    member = Member.query.get_or_404(memberid)

    member_participated_events = Participate.query.join(Race, Participate.raceid == Race.raceid) \
        .join(Event, Event.eventid == Race.eventid) \
        .add_columns(Event.eventid, Event.name, Event.startdate, Event.state, Event.country, Race.name.label('rname'), Participate.finishedtime, Participate.memberid) \
        .filter(Participate.memberid == member.memberid) \
        .order_by(Event.startdate)

    member_image = app.config['CLOUD_STORAGE_URL'] + url_for('static', filename='profile_pics/' + member.pic)
    today = date.today()
    member_age = today.year - member.bdate.year - ((today.month, today.day) < (member.bdate.month, member.bdate.day))
    return render_template('runner_detail.html', image_file = member_image, member = member, age = member_age, participated_events = member_participated_events)


@app.route("/search_runner")
def search_runner():
    import re
    import mysql.connector
    from mysql.connector import Error

    name = request.args.get('name', default = '', type = str)
    sex  = request.args.get( 'sex', default = 0, type = int)
    age  = request.args.get( 'age', default = 0, type = int)
    last = request.args.get('last', default = 0, type = int)
    hist = request.args.get('hist', default = 0, type = int)

    runner_query = """
        SELECT members.memberid, members.fname, members.lname, members.pic, 
            members.gender, TIMESTAMPDIFF(YEAR, members.bdate, CURDATE()) AS age, 
            members.state, members.country, members.club, 
            race.endtime 
        FROM members 
        LEFT JOIN participate ON members.memberid = participate.memberid 
        LEFT JOIN race ON participate.raceid = race.raceid 
        WHERE {formatted_where} 
        GROUP BY members.memberid 
        HAVING {formatted_having} 
        ORDER BY members.fname, members.lname 
        """
    where_conditions = " TRUE "
    having_conditions = " TRUE "

    # input string filter to avoid SQL injection !!!
    if name:
        where_conditions += "\n            AND (TRUE "
        name_list = re.split(r"[^a-zA-Z0-9]", name)
        for name_item in name_list :
            if name_item :
                x = """\n                AND (FALSE 
                    OR members.fname        REGEXP '^{name_item}|[^a-zA-Z0-9]{name_item}' 
                    OR members.lname        REGEXP '^{name_item}|[^a-zA-Z0-9]{name_item}' 
                    OR members.city         REGEXP '^{name_item}|[^a-zA-Z0-9]{name_item}' 
                    OR members.state        REGEXP '^{name_item}|[^a-zA-Z0-9]{name_item}' 
                    OR members.country      REGEXP '^{name_item}|[^a-zA-Z0-9]{name_item}' 
                    OR members.club         REGEXP '^{name_item}|[^a-zA-Z0-9]{name_item}' 
                )"""
                where_conditions += x.format(name_item=name_item)
        where_conditions += "\n            )"

    if sex > 0 :
        where_conditions += "\n            AND (FALSE "
        if sex & 0x0001:
            where_conditions += "\n                OR members.gender = 'M' "
        if sex & 0x0002:
            where_conditions += "\n                OR members.gender = 'F' "
        where_conditions += "\n            )"

    if age > 0 :
        where_conditions += "\n            AND (FALSE "
        if age & 0x0001:
            where_conditions += "\n                OR (TIMESTAMPDIFF(YEAR, members.bdate, CURDATE()) < 20) "
        if age & 0x0002:
            where_conditions += "\n                OR (TIMESTAMPDIFF(YEAR, members.bdate, CURDATE()) >= 20 AND TIMESTAMPDIFF(YEAR, members.bdate, CURDATE()) < 30) "
        if age & 0x0004:
            where_conditions += "\n                OR (TIMESTAMPDIFF(YEAR, members.bdate, CURDATE()) >= 30 AND TIMESTAMPDIFF(YEAR, members.bdate, CURDATE()) < 40) "
        if age & 0x0008:
            where_conditions += "\n                OR (TIMESTAMPDIFF(YEAR, members.bdate, CURDATE()) >= 40 AND TIMESTAMPDIFF(YEAR, members.bdate, CURDATE()) < 50) "
        if age & 0x0010:
            where_conditions += "\n                OR (TIMESTAMPDIFF(YEAR, members.bdate, CURDATE()) >= 50 AND TIMESTAMPDIFF(YEAR, members.bdate, CURDATE()) < 60) "
        if age & 0x0020:
            where_conditions += "\n                OR (TIMESTAMPDIFF(YEAR, members.bdate, CURDATE()) >= 60 AND TIMESTAMPDIFF(YEAR, members.bdate, CURDATE()) < 70) "
        if age & 0x0040:
            where_conditions += "\n                OR (TIMESTAMPDIFF(YEAR, members.bdate, CURDATE()) >= 70) "
        where_conditions += "\n            )"

    if hist > 0 :
        having_conditions += "\n            AND (FALSE "
        if hist & 0x0001:
            having_conditions += "\n                OR (COUNT(IF(race.endtime < NOW(), 1, NULL)) > 50) "
        if hist & 0x0002:
            having_conditions += "\n                OR (COUNT(IF(race.endtime < NOW(), 1, NULL)) > 20 AND COUNT(IF(race.endtime < NOW(), 1, NULL)) <= 50) "
        if hist & 0x0004:
            having_conditions += "\n                OR (COUNT(IF(race.endtime < NOW(), 1, NULL)) > 5  AND COUNT(IF(race.endtime < NOW(), 1, NULL)) <= 20) "
        if hist & 0x0008:
            having_conditions += "\n                OR (COUNT(IF(race.endtime < NOW(), 1, NULL)) > 0  AND COUNT(IF(race.endtime < NOW(), 1, NULL)) <= 5) "
        if hist & 0x0010:
            having_conditions += "\n                OR (COUNT(IF(race.endtime < NOW(), 1, NULL)) = 0) "
        having_conditions += "\n            )"

    if last > 0 :
        having_conditions += "\n            AND (FALSE "
        if last & 0x0001:
            having_conditions += "\n                OR (MAX(IF(race.endtime < NOW(), race.endtime, NULL)) >= DATE_ADD(NOW(), INTERVAL -1 YEAR)) "
        if last & 0x0002:
            having_conditions += "\n                OR (MAX(IF(race.endtime < NOW(), race.endtime, NULL)) >= DATE_ADD(NOW(), INTERVAL -3 YEAR)) "
        if last & 0x0004:
            having_conditions += "\n                OR (MAX(IF(race.endtime < NOW(), race.endtime, NULL)) >= DATE_ADD(NOW(), INTERVAL -5 YEAR)) "
        if last & 0x0008:
            having_conditions += "\n                OR (MAX(IF(race.endtime < NOW(), race.endtime, NULL)) <  DATE_ADD(NOW(), INTERVAL -5 YEAR)) "
        if last & 0x0010:
            having_conditions += "\n                OR (MAX(IF(race.endtime < NOW(), race.endtime, NULL)) IS NULL) "
        having_conditions += "\n            )"

    formatted_where = where_conditions.format()
    formatted_having = having_conditions.format()
    formatted_query = runner_query.format(formatted_where=formatted_where, formatted_having=formatted_having)
    print(formatted_query)

    conn = None
    search_results = []
    try :
        conn = mysql.connector.connect(host=mysql_connect_host,
                                       database=mysql_connect_database,
                                       user=mysql_connect_user,
                                       password=mysql_connect_password)
        if conn.is_connected() :
            cursor = conn.cursor(dictionary=True)
            cursor.execute(formatted_query)
            search_results = cursor.fetchall()
            #print(search_results)
    except Error as e :
        print(e)
    finally :
        if conn : conn.close()

    return render_template('search_runner.html', outString = search_results)


@app.route('/search_runner/')
@app.route('/search_runner/<name>')
def fetch_runner(name = ''):
    today = date.today()
    search_results = Member.query.filter((Member.fname.contains(name)) | (Member.lname.contains(name))).all()
    runner_list = []
    for runner in search_results:
        runner_dict = {}
        runner_dict['pic'] = runner.pic
        runner_dict['memberid'] = runner.memberid
        runner_dict['name'] = runner.fname + ' ' + runner.lname
        runner_dict['gender'] = runner.gender
        runner_dict['age'] = today.year - runner.bdate.year - ((today.month, today.day) < (runner.bdate.month, runner.bdate.day))
        runner_dict['location'] = (runner.state if runner.state else '') + ' ' + (runner.country if runner.country else '')
        runner_dict['club'] = runner.club
        runner_list.append(runner_dict)
    
    return jsonify({'runners' : runner_list})


@app.route("/search_event")
def search_event():
    import re
    import mysql.connector
    from mysql.connector import Error

    name = request.args.get('name', default = '', type = str)
    past = request.args.get('past', default = 0, type = int)
    open = request.args.get('open', default = 0, type = int)
    mont = request.args.get('mont', default = 0, type = int)
    diff = request.args.get('diff', default = 0, type = int)
    dist = request.args.get('dist', default = 0, type = int)
    dura = request.args.get('dura', default = 0, type = int)

    event_query = """
        SELECT events.eventid, events.name, events.logo, 
            events.startdate, events.enddate, events.regopendate, events.regclosedate, 
            events.state, events.country, events.organization, 
            CONCAT(GROUP_CONCAT(DISTINCT race.distance ORDER BY race.distance ASC SEPARATOR 'mi, '), 'mi') AS racelist 
        FROM events 
        LEFT JOIN race ON events.eventid = race.eventid 
        WHERE {formatted_where} 
        GROUP BY events.eventid 
        ORDER BY events.startdate 
        """
    where_conditions = " TRUE "

    # input string filter to avoid SQL injection !!!
    if name:
        where_conditions += "\n            AND (TRUE "
        name_list = re.split(r"[^a-zA-Z0-9]", name)
        for name_item in name_list :
            if name_item :
                x = """\n                AND (FALSE 
                    OR events.name         REGEXP '^{name_item}|[^a-zA-Z0-9]{name_item}' 
                    OR events.city         REGEXP '^{name_item}|[^a-zA-Z0-9]{name_item}' 
                    OR events.state        REGEXP '^{name_item}|[^a-zA-Z0-9]{name_item}' 
                    OR events.country      REGEXP '^{name_item}|[^a-zA-Z0-9]{name_item}' 
                    OR events.organization REGEXP '^{name_item}|[^a-zA-Z0-9]{name_item}' 
                    OR CAST(YEAR(events.startdate) AS CHAR) = '{name_item}' 
                )"""
                where_conditions += x.format(name_item=name_item)
        where_conditions += "\n            )"

    if past & 1 :
        where_conditions += "\n            AND events.enddate >= '2000-01-01' "
    else :
        where_conditions += "\n            AND events.enddate >= CURDATE() "

    if open & 1 :
        where_conditions += "\n            AND events.regopendate <= CURDATE() AND events.regclosedate >= CURDATE() "

    if mont > 0 :
        where_conditions += "\n            AND (FALSE "
        if mont & 0x0001:
            where_conditions += "\n                OR MONTH(events.startdate) = 1 "
        if mont & 0x0002:
            where_conditions += "\n                OR MONTH(events.startdate) = 2 "
        if mont & 0x0004:
            where_conditions += "\n                OR MONTH(events.startdate) = 3 "
        if mont & 0x0008:
            where_conditions += "\n                OR MONTH(events.startdate) = 4 "
        if mont & 0x0010:
            where_conditions += "\n                OR MONTH(events.startdate) = 5 "
        if mont & 0x0020:
            where_conditions += "\n                OR MONTH(events.startdate) = 6 "
        if mont & 0x0040:
            where_conditions += "\n                OR MONTH(events.startdate) = 7 "
        if mont & 0x0080:
            where_conditions += "\n                OR MONTH(events.startdate) = 8 "
        if mont & 0x0100:
            where_conditions += "\n                OR MONTH(events.startdate) = 9 "
        if mont & 0x0200:
            where_conditions += "\n                OR MONTH(events.startdate) = 10 "
        if mont & 0x0400:
            where_conditions += "\n                OR MONTH(events.startdate) = 11 "
        if mont & 0x0800:
            where_conditions += "\n                OR MONTH(events.startdate) = 12 "
        where_conditions += "\n            )"

    if dist > 0:
        where_conditions += "\n            AND (FALSE "
        if dist & 0x0001:
            where_conditions += "\n                OR (race.distance >= 0  AND race.distance < 11) "
        if dist & 0x0002:
            where_conditions += "\n                OR (race.distance >= 11 AND race.distance < 31) "
        if dist & 0x0004:
            where_conditions += "\n                OR (race.distance >= 31 AND race.distance < 51) "
        if dist & 0x0008:
            where_conditions += "\n                OR (race.distance >= 51 AND race.distance < 111) "
        if dist & 0x0010:
            where_conditions += "\n                OR (race.distance >= 111) "
        where_conditions += "\n            )"

    if dura > 0:
        where_conditions += "\n            AND (FALSE "
        if dura & 0x0001:
            where_conditions += "\n                OR (HOUR(TIMEDIFF(race.endtime, race.starttime)) >= 0  AND HOUR(TIMEDIFF(race.endtime, race.starttime)) < 13) "
        if dura & 0x0002:
            where_conditions += "\n                OR (HOUR(TIMEDIFF(race.endtime, race.starttime)) >= 13 AND HOUR(TIMEDIFF(race.endtime, race.starttime)) < 25) "
        if dura & 0x0004:
            where_conditions += "\n                OR (HOUR(TIMEDIFF(race.endtime, race.starttime)) >= 25 AND HOUR(TIMEDIFF(race.endtime, race.starttime)) < 73) "
        if dura & 0x0008:
            where_conditions += "\n                OR (HOUR(TIMEDIFF(race.endtime, race.starttime)) >= 73) "
        where_conditions += "\n            )"

    formatted_where = where_conditions.format()
    formatted_query = event_query.format(formatted_where=formatted_where)
    print(formatted_query)

    conn = None
    search_results = []
    try :
        conn = mysql.connector.connect(host=mysql_connect_host,
                                       database=mysql_connect_database,
                                       user=mysql_connect_user,
                                       password=mysql_connect_password)
        if conn.is_connected() :
            cursor = conn.cursor(dictionary=True)
            cursor.execute(formatted_query)
            search_results = cursor.fetchall()
            #print(search_results)
    except Error as e :
        print(e)
    finally :
        if conn : conn.close()

    return render_template('search_event.html', outString = search_results)


@app.route('/search_event/')
@app.route('/search_event/<name>')
def fetch_event(name = ''):
    search_results = Event.query.filter((Event.name.contains(name))).all()
    event_list = []
    for event in search_results:
        event_dict = {}
        event_dict['logo'] = event.logo
        event_dict['eventid'] = event.eventid
        event_dict['name'] = event.name
        event_dict['startdate'] = event.startdate.isoformat()
        event_dict['year'] = event.startdate.year
        event_dict['regopendate'] = event.regopendate.isoformat()
        event_dict['location'] = (event.state if event.state else '') + ' ' + (event.country if event.country else '')
        event_dict['organization'] = event.organization
        event_list.append(event_dict)
    
    return jsonify({'events' : event_list})


###################################################################################################


@app.route("/event/<eventid>/race/new", methods=['GET', 'POST'])
@login_required
def new_race(eventid):
    event = Event.query.get_or_404(eventid)
    member = Member.query.filter_by(userid = current_user.id).first()

    if member is None or member.memberid != event.memberid:
        flash('You are not allowed to add a race!', 'danger')
        return redirect(url_for('event', eventid=eventid))

    current_event_image = app.config['CLOUD_STORAGE_URL'] + url_for('static', filename='event_pics/' + event.logo)
    form = RaceNewForm()
    if form.validate_on_submit():
        race = Race(name = form.field_name.data, distance = form.field_distance.data,
             starttime = form.field_starttime.data, endtime = form.field_endtime.data,
             capacity = form.field_capacity.data, price = form.field_price.data,
             description = form.field_description.data,
             eventid = eventid)
        db.session.add(race)
        db.session.commit()
        flash('You have added a new race!', 'success')
        return redirect(url_for('event', eventid=eventid))
    elif request.method == 'GET':
        form.field_starttime.data = datetime.now()
        form.field_endtime.data = datetime.now()
    return render_template('create_race.html', title='Add Race', form=form, event=event, image_file=current_event_image, legend='Race Info')


@app.route("/event/<eventid>/race/<raceid>/update", methods=['GET', 'POST'])
@login_required
def update_race(eventid, raceid):
    event  = Event.query.get_or_404(eventid)
    race   = Race.query.get_or_404(raceid)
    member = Member.query.filter_by(userid = current_user.id).first()

    if member is None or member.memberid != event.memberid or race.eventid != event.eventid:
        flash('You are not allowed to update the race!', 'danger')
        return redirect(url_for('event', eventid=eventid))
    
    current_event_image = app.config['CLOUD_STORAGE_URL'] + url_for('static', filename='event_pics/' + event.logo)
    form = RaceUpdateForm()
    if form.validate_on_submit():
        race.name = form.field_name.data
        race.distance = form.field_distance.data
        race.starttime = form.field_starttime.data
        race.endtime = form.field_endtime.data
        race.capacity = form.field_capacity.data
        race.price = form.field_price.data
        race.description = form.field_description.data
        db.session.commit()
        flash('The race has been updated!', 'success')
        return redirect(url_for('event', eventid=eventid))
    elif request.method == 'GET':
        form.field_name.data = race.name
        form.field_distance.data = race.distance
        form.field_starttime.data = race.starttime
        form.field_endtime.data = race.endtime
        form.field_capacity.data = race.capacity
        form.field_price.data = race.price
        form.field_description.data = race.description
    return render_template('create_race.html', title='Update Race', form=form, event=event, image_file=current_event_image, legend='Race Info')


@app.route("/event/<eventid>/race/<raceid>/delete", methods=['GET', 'POST'])
@login_required
def delete_race(eventid, raceid):
    event  = Event.query.get_or_404(eventid)
    race   = Race.query.get_or_404(raceid)
    member = Member.query.filter_by(userid = current_user.id).first()

    if member is None or member.memberid != event.memberid or race.eventid != event.eventid:
        flash('You are not allowed to delete the race!', 'danger')
        return redirect(url_for('event', eventid=eventid))

    try :
        db.session.delete(race)
        db.session.commit()
        flash('The race has been deleted!', 'success')
    except :
        flash('The race cannot been deleted!', 'danger')
    return redirect(url_for('event', eventid=eventid))


@app.route("/event/<eventid>/registeration", methods=['GET', 'POST'])
@login_required
def register_race(eventid):
    event  = Event.query.get_or_404(eventid)
    member = Member.query.filter_by(userid = current_user.id).first()

    if member is None:
        flash('You have to become a member! Click Membership in My Account', 'danger')
        return redirect(url_for('event', eventid=eventid))

    if event.regopendate > date.today() :
        flash('The registion is not open!', 'danger')
        return redirect(url_for('event', eventid=eventid))

    if event.regclosedate < date.today() :
        flash('The registion is closed!', 'danger')
        return redirect(url_for('event', eventid=eventid))

    form = RaceRegisterForm()
    form.field_raceid.choices = [('', '-- please select a race --')]
    form.field_raceid.choices += [(a.raceid, a.name) for a in Race.query.filter_by(eventid=eventid)]
    if form.validate_on_submit():
        old_part = Participate.query.filter_by(memberid=member.memberid).filter_by(raceid=form.field_raceid.data).first()
        if old_part is None:
            plannedtime = str(form.field_plannedhour.data) + ':' + str(form.field_plannedminute.data)
            new_part = Participate(tshirtsize = form.field_tshirtsize.data, plannedtime = plannedtime,
                memberid = member.memberid, raceid = form.field_raceid.data)
            db.session.add(new_part)
            db.session.commit()
            flash('You have successfully registered a new race!', 'success')
        else :
            flash('You have already registered that race before!', 'danger')
        return redirect(url_for('event', eventid=eventid))
    
    current_event_image = app.config['CLOUD_STORAGE_URL'] + url_for('static', filename='event_pics/' + event.logo)
    return render_template('register_race.html', title='Register Race', form=form, event=event, image_file=current_event_image, legend='Registration Info')


@app.route("/event/<eventid>/volunteering")
@login_required
def list_job(eventid):
    import mysql.connector
    from mysql.connector import Error

    event = Event.query.get_or_404(eventid)
    member = Member.query.filter_by(userid = current_user.id).first()

    if member is None:
        flash('You have to become a member! Click Membership in My Account', 'danger')
        return redirect(url_for('event', eventid=eventid))

    if member.memberid == event.memberid :
        race_director = True
    else :
        race_director = False

    job_query = """
        SELECT jobrequestid, j1.jobtypeid, name, headcount, detail, title, description, 
             headcount - (SELECT COUNT(memberid) FROM apply WHERE jobrequestid = j1.jobrequestid) AS available, 
             EXISTS (SELECT memberid FROM apply WHERE jobrequestid = j1.jobrequestid AND memberid = %(memberid)s) AS applied 
        FROM jobrequest j1 
        JOIN jobtype ON j1.jobtypeid = jobtype.jobtypeid 
        WHERE eventid = %(eventid)s 
        ORDER BY j1.jobtypeid 
        """

    conn = None
    search_results = []
    try :
        conn = mysql.connector.connect(host=mysql_connect_host,
                                       database=mysql_connect_database,
                                       user=mysql_connect_user,
                                       password=mysql_connect_password)
        if conn.is_connected() :
            cursor = conn.cursor(dictionary=True)
            cursor.execute(job_query, {'eventid': eventid, 'memberid': member.memberid})
            search_results = cursor.fetchall()
            #print(search_results)
    except Error as e :
        print(e)
    finally :
        if conn : conn.close()

    current_event_logo = app.config['CLOUD_STORAGE_URL'] + url_for('static', filename='event_pics/' + event.logo)
    return render_template('list_job.html', title=event.name, event=event, jobs=search_results, logo_file=current_event_logo, race_director=race_director)


@app.route("/event/<eventid>/job/new", methods=['GET', 'POST'])
@login_required
def new_job(eventid):
    event = Event.query.get_or_404(eventid)
    member = Member.query.filter_by(userid = current_user.id).first()

    if member is None or member.memberid != event.memberid:
        flash('You are not allowed to add a job!', 'danger')
        return redirect(url_for('event', eventid=eventid))
    
    form = JobRequestNewForm()
    form.field_jobtypeid.choices = [('', '-- please select a job title --')]
    form.field_jobtypeid.choices += [(a.jobtypeid, a.title) for a in Jobtype.query.all()]
    if form.validate_on_submit():
        jobrequest = Jobrequest(jobtypeid = form.field_jobtypeid.data, name = form.field_name.data,
            headcount = form.field_headcount.data, detail = form.field_detail.data,
            eventid = eventid)
        db.session.add(jobrequest)
        db.session.commit()
        flash('You have added a new job!', 'success')
        return redirect(url_for('event', eventid=eventid))
    
    current_event_image = app.config['CLOUD_STORAGE_URL'] + url_for('static', filename='event_pics/' + event.logo)
    return render_template('create_job.html', title='Add Job', form=form, event=event, image_file=current_event_image, legend='Job Info')


@app.route("/event/<eventid>/job/<jobrequestid>/update", methods=['GET', 'POST'])
@login_required
def update_job(eventid, jobrequestid):
    event  = Event.query.get_or_404(eventid)
    jobrequest = Jobrequest.query.get_or_404(jobrequestid)
    member = Member.query.filter_by(userid = current_user.id).first()

    if member is None or member.memberid != event.memberid or jobrequest.eventid != event.eventid:
        flash('You are not allowed to update the job!', 'danger')
        return redirect(url_for('list_job', eventid=eventid))
    
    form = JobRequestUpdateForm()
    form.field_jobtypeid.choices = [('', '-- please select a job title --')]
    form.field_jobtypeid.choices += [(a.jobtypeid, a.title) for a in Jobtype.query.all()]
    if form.validate_on_submit():
        jobrequest.jobtypeid = form.field_jobtypeid.data
        jobrequest.name = form.field_name.data
        jobrequest.headcount = form.field_headcount.data
        jobrequest.detail = form.field_detail.data
        db.session.commit()
        flash('The job has been updated!', 'success')
        return redirect(url_for('list_job', eventid=eventid))
    elif request.method == 'GET':
        form.field_jobtypeid.data = str(jobrequest.jobtypeid)
        form.field_name.data = jobrequest.name
        form.field_headcount.data = jobrequest.headcount
        form.field_detail.data = jobrequest.detail

    current_event_image = app.config['CLOUD_STORAGE_URL'] + url_for('static', filename='event_pics/' + event.logo)
    return render_template('create_job.html', title='Update Job', form=form, event=event, image_file=current_event_image, legend='Job Info')


@app.route("/event/<eventid>/job/<jobrequestid>/delete", methods=['GET', 'POST'])
@login_required
def delete_job(eventid, jobrequestid):
    event  = Event.query.get_or_404(eventid)
    jobrequest = Jobrequest.query.get_or_404(jobrequestid)
    member = Member.query.filter_by(userid = current_user.id).first()

    if member is None or member.memberid != event.memberid or jobrequest.eventid != event.eventid:
        flash('You are not allowed to delete the job!', 'danger')
        return redirect(url_for('list_job', eventid=eventid))

    try :
        db.session.delete(jobrequest)
        db.session.commit()
        flash('The job has been deleted!', 'success')
    except :
        flash('The job cannot been deleted!', 'danger')
    return redirect(url_for('list_job', eventid=eventid))


@app.route("/event/<eventid>/job/<jobrequestid>/apply", methods=['GET', 'POST'])
@login_required
def apply_job(eventid, jobrequestid):
    event  = Event.query.get_or_404(eventid)
    jobrequest = Jobrequest.query.get_or_404(jobrequestid)
    member = Member.query.filter_by(userid = current_user.id).first()

    if member is None or jobrequest.eventid != event.eventid :
        flash('You are not allowed to apply the job!', 'danger')
        return redirect(url_for('list_job', eventid=eventid))

    old_apply = Apply.query.filter_by(memberid=member.memberid).filter_by(jobrequestid=jobrequestid).first()
    if old_apply is None:
        new_apply = Apply(memberid=member.memberid, jobrequestid=jobrequestid,
            appliedtime = datetime.now())
        db.session.add(new_apply)
        db.session.commit()
        flash('You have successfully applied a new job!', 'success')
    else :
        flash('You have already applied that job before!', 'danger')
    return redirect(url_for('list_job', eventid=eventid))


@app.route("/event/<eventid>/job/<jobrequestid>/drop", methods=['GET', 'POST'])
@login_required
def drop_job(eventid, jobrequestid):
    event  = Event.query.get_or_404(eventid)
    jobrequest = Jobrequest.query.get_or_404(jobrequestid)
    member = Member.query.filter_by(userid = current_user.id).first()

    if member is None or jobrequest.eventid != event.eventid:
        flash('You are not allowed to drop the job!', 'danger')
        return redirect(url_for('list_job', eventid=eventid))

    old_apply = Apply.query.filter_by(memberid=member.memberid).filter_by(jobrequestid=jobrequestid).first()
    if old_apply:
        db.session.delete(old_apply)
        db.session.commit()
    flash('You have successfully dropped that job!', 'success')
    return redirect(url_for('list_job', eventid=eventid))

