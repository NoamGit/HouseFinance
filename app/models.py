from datetime import datetime
from time import time

import jwt

from app import db, app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import login
from hashlib import md5


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
                          , app.config['SECRET_KEY'], algorithm='HS256').decode('utf-8')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, app.config['SECRET_KEY']
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


class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_name = db.Column(db.String(128), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    price = db.Column(db.Float, nullable=True)
    payment_price = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    category = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)

    def set_category(self, category_id:int):
        self.category = category_id

    def __repr__(self):
        return f"<Purchase {self.date}::{self.business_name}::{self.price}>"


# region helper functions

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

# endregion
