import googlemaps
from flask import Flask, render_template, flash, redirect, url_for, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_, and_
from sqlalchemy.testing import in_
from werkzeug.urls import url_parse
from datetime import datetime

from wtforms import TextAreaField, SelectField, SubmitField,HiddenField

from app import app, db, gmaps
from app.email import send_password_reset_email
from app.forms import LoginForm, RegistrationForm, EditProfileForm, PurchaseForm, ResetPasswordRequestForm, \
    ResetPasswordForm, CategoryForm
from app.models import User, Purchase, Category
from flask_login import current_user, login_user, logout_user, login_required
from config import Config


@app.route('/findplace', methods=['POST'])
@login_required
def find_place():
    business_name = request.form['text'].strip()
    res = gmaps.find_place(input=business_name, input_type='textquery'
                           , fields=['formatted_address', 'icon', 'name'
                                    , 'permanently_closed'
                                    , 'types'
                                    , 'geometry/location'])['candidates']
    if len(res) == 0:
        return jsonify({'info': "No match in google API"})
    else:
        info = f"Business: {res[0]['name']}\n" \
               f"Address: {res[0]['formatted_address']}\n" \
               f"Types: {' | '.join(res[0]['types'])}"

    return jsonify({'info': info})
    # return jsonify({'info': res['name'], 'address': res['formatted_address'], 'type': res['types']})


@app.route('/annotate', methods=['GET', 'POST'])
@login_required
def annotate():
    class F(CategoryForm):
        pass

    page = request.args.get('page', 1, type=int)
    purchases = Purchase.query.filter_by(buyer=current_user, business_category=None) \
        .order_by(Purchase.date.desc()) \
        .paginate(page, app.config['ANNOTATIONS_PER_PAGE'], False)
    # .group_by(Purchase.business_name)\
    categories = Category.query.filter(or_(Category.user_id == current_user.id, Category.user_id == None))
    next_url = url_for('annotate', page=purchases.next_num) if purchases.has_next else None
    prev_url = url_for('annotate', page=purchases.prev_num) if purchases.prev_num else None

    default_category_list = [(0, '')] + [(x.id, x.category) for x in categories.all()]
    default_category_dict = dict(default_category_list)
    last_category_dict = {p.business_name: p.category for p in \
                          Purchase.query.filter(
                              and_(Purchase.buyer == current_user, Purchase.business_category != None)) \
                              .group_by(Purchase.business_name).all()}

    # dynamically build form
    for p in purchases.items:
        cat = default_category_list.copy()
        cat_id = last_category_dict.get(p.business_name)
        if cat_id is not None:
            cat_tuple = (cat_id, default_category_dict[cat_id])
            cat.remove(cat_tuple)
            cat.insert(0, cat_tuple)
        setattr(F, f"business_name_{p.id}", HiddenField(f"{p.business_name}"))
        setattr(F, f"purchase_{p.id}", SelectField("₪ {:.1f}".format(p.payment_price) + \
                                                   f" | {p.date.strftime('%a %Y-%m-%d')}",
                                                   choices=cat))
    setattr(F, "submit", SubmitField('Submit'))
    form = F()

    # action when submitted
    if form.is_submitted():
        items_key = [k for k in form.data.keys() if 'purchase' in k]
        for p in items_key:
            cat_value = form.data.get(p)
            if cat_value != str(0) and cat_value != 'None':
                purchase_id = p.split('_')[-1]
                purchase = Purchase.query.filter(Purchase.id == purchase_id)
                purchase.first().set_category(int(cat_value))
        db.session.commit()
        flash('Categories were updated!')
        # next_page = request.args.get('next')
        # if not next_page or url_parse(next_page).netloc != '':
        #     next_page = url_for('annotate')
        # return redirect(next_page)
        return redirect(url_for('annotate'))

    return render_template('annotate.html', form=form, purhcases=purchases.items, next_url=next_url,
                           prev_url=prev_url)


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        current_user.username = current_user.username
    return render_template('edit_profile.html', title='Edit Profile', form=form)


@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = PurchaseForm()
    if form.validate_on_submit():
        purchase = Purchase(business_name=form.business_name.data
                            , date=form.date.data  # .strftime('%Y-%m-%d')
                            , price=form.price.data
                            , payment_price=form.payment_price.data
                            , buyer=current_user)
        db.session.add(purchase)
        db.session.commit()
        flash('Purchase was commited!')
        return redirect(url_for('index'))

    page = request.args.get('page', 1, type=int)
    purchases = Purchase.query.filter_by(buyer=current_user).order_by(Purchase.date.desc()).paginate(page, app.config[
        'PURCHASES_PER_PAGE'], False)
    next_url = url_for('index', page=purchases.next_num) if purchases.has_next else None
    prev_url = url_for('index', page=purchases.prev_num) if purchases.prev_num else None
    return render_template('index.html', title='Home', form=form, purchases=purchases.items, next_url=next_url,
                           prev_url=prev_url)


@app.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    purchases = Purchase.query.filter_by(buyer=user).order_by(Purchase.date.desc()).paginate(page, app.config[
        'PURCHASES_PER_PAGE'], False)
    next_url = url_for('user', username=user.username, page=purchases.next_num) if purchases.has_next else None
    prev_url = url_for('user', username=user.username, page=purchases.prev_num) if purchases.prev_num else None
    return render_template('user.html', user=user, purchases=purchases.items, next_url=next_url,
                           prev_url=prev_url)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(f"Congrats, {form.username.data} you are now registered!")
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        redirect(url_for('index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash('Check your email for the instructions to reset password')
        return redirect(url_for('login'))
    return render_template('reset_password_request.html', title='Reset Password', form=form)


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        redirect(url_for('index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset')
        return redirect(url_for('login'))
    return render_template('reset_password.html', form=form)
