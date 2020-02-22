from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField \
    , SubmitField, FloatField, TextAreaField, SelectField
from wtforms.fields.html5 import DateField

from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length, Optional

from app.models import User


class CategoryForm(FlaskForm):
    # categories = [('food',3),('insurance',4)]
    # category = SelectField(choices=categories)

    def append_field(self, name, field):
        setattr(self, name, field)
        return self


class EditProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    submit = SubmitField('Submit')

    def __init__(self, original_username, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class ResetPasswordRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Request Password Reset')


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')


class PurchaseForm(FlaskForm):
    business_name = StringField('Business Name', validators=[DataRequired(), Length(min=1, max=140)])
    date = DateField('Purchase Date', format='%Y-%m-%d', validators=[DataRequired()])
    payment_price = FloatField("Payed Price", validators=[DataRequired()])
    price = FloatField("Full Price", validators=[Optional()])
    submit = SubmitField('Submit')
