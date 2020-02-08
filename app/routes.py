from flask import Flask, render_template, flash, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from werkzeug.urls import url_parse
from datetime import datetime
from app import app, db
from app.email import send_password_reset_email
from app.forms import LoginForm, RegistrationForm, EditProfileForm, PurchaseForm, ResetPasswordRequestForm, \
    ResetPasswordForm
from app.models import User, Purchase
from flask_login import current_user, login_user, logout_user, login_required
from config import Config


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

@app.route('/reset_password/<token>', methods=['GET','POST'])
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
