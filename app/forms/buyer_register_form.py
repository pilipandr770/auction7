from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo

class BuyerRegisterForm(FlaskForm):
    username = StringField('Ім\'я', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    confirm_password = PasswordField('Підтвердити пароль', validators=[EqualTo('password')])
    submit = SubmitField('Зареєструватися як покупець')
