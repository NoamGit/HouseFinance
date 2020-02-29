from datetime import datetime
from time import time

import jwt
from flask import current_app

from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import login
from hashlib import md5
from app.search import add_to_index

from app.search import query_index, remove_from_index


class SearchableMixin():
    @classmethod
    def search(cls, expression, page, per_page):
        ids, total = query_index(cls.__tablename__, expression, page, per_page)
        if total == 0:
            return cls.query.filter_by(id=0), 0
        when = []
        for k in range(len(ids)):
            when.append((ids[k], k))
        return cls.query.filter(cls.id.in_(ids)).order_by(db.case(when, value=cls.id)), total

    @classmethod
    def before_commit(cls, session):
        session._changes = {
            'add': list(session.new)
            , 'update': list(session.dirty)
            , 'delete': list(session.deleted)
        }

    @classmethod
    def after_commit(cls, session):
        for obj in session._changes['add']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)

        for obj in session._changes['update']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)
        session._changes = None

    @classmethod
    def reindex(cls):
        for obj in cls.query:
            add_to_index(cls.__tablename__, obj)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    purchases = db.relationship('Purchase', backref='buyer', lazy='dynamic')
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode({'reset_password': self.id, 'exp': time() + expires_in}
                          , current_app.config['SECRET_KEY'], algorithm='HS256').decode('utf-8')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY']
                            , algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)

    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest() if self.email is not None else ''
        return f'https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}'

    def __repr__(self):
        return f"<User {self.username}>"


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(64), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    purchase = db.relationship('Purchase', backref='business_category', lazy='dynamic')

    def __repr__(self):
        return f"<Category {self.category}::{self.purchase}>"


class Purchase(SearchableMixin, db.Model):
    __searchable__ = ['business_name']
    id = db.Column(db.Integer, primary_key=True)
    business_name = db.Column(db.String(128), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    price = db.Column(db.Float, nullable=True)
    payment_price = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    category = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)

    def set_category(self, category_id: int):
        self.category = category_id

    def __repr__(self):
        return f"<Purchase {self.date}::{self.business_name}::{self.price}>"


# region helper functions

@login.user_loader
def load_user(id):
    return User.query.get(int(id))


# endregion

db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)
