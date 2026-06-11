
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo

class RoleSelectForm(FlaskForm):
    user_type = SelectField('Kontotyp', choices=[('buyer', 'Käufer'), ('seller', 'Verkäufer')], validators=[DataRequired()])
    submit = SubmitField('Weiter')

class BuyerRegisterForm(FlaskForm):
    username = StringField('Benutzername', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Passwort', validators=[DataRequired()])
    confirm_password = PasswordField('Passwort bestätigen', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Registrieren')
