from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FileField
from wtforms.validators import DataRequired, Email, EqualTo

class SellerRegisterForm(FlaskForm):
    username = StringField('Ім\'я', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    confirm_password = PasswordField('Підтвердити пароль', validators=[EqualTo('password')])
    company_name = StringField('Назва компанії', validators=[DataRequired()])
    tax_id = StringField('VAT номер', validators=[DataRequired()])
    verification_document = FileField('Документ для верифікації', validators=[DataRequired()])
    submit = SubmitField('Зареєструватися як продавець')
    