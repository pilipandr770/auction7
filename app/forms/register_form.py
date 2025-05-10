# app/forms/register_form.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo

class RegisterForm(FlaskForm):
    username = StringField('Ім\'я користувача', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    confirm_password = PasswordField('Підтвердіть пароль', validators=[DataRequired(), EqualTo('password')])
    user_type = SelectField('Тип користувача', choices=[('buyer', 'Покупець'), ('seller', 'Продавець')], validators=[DataRequired()])
    submit = SubmitField('Зареєструватися')
