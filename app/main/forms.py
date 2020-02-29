from flask import request
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, ValidationError, FloatField
from wtforms.fields.html5 import DateField
from wtforms.validators import DataRequired, Length, Optional

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


class PurchaseForm(FlaskForm):
    business_name = StringField('Business Name', validators=[DataRequired(), Length(min=1, max=140)])
    date = DateField('Purchase Date', format='%Y-%m-%d', validators=[DataRequired()])
    payment_price = FloatField("Payed Price", validators=[DataRequired()])
    price = FloatField("Full Price", validators=[Optional()])
    submit = SubmitField('Submit')


class SearchForm(FlaskForm):
    q = StringField('Search', validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        if 'formdata' not in kwargs:
            kwargs['formdata'] = request.args
        if 'csrf_enabled' not in kwargs:
            kwargs['csrf_enabled'] = False
        super(SearchForm, self).__init__(*args, **kwargs)
