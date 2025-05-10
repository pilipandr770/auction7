
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Email
from flask_wtf.file import FileField, FileAllowed

class SellerRegisterForm(FlaskForm):
    company_name = StringField('Назва компанії', validators=[DataRequired()])
    registration_number = StringField('Реєстраційний номер', validators=[DataRequired()])
    country = StringField('Країна реєстрації', validators=[DataRequired()])
    company_address = StringField('Адреса компанії', validators=[DataRequired()])
    tax_id = StringField('Податковий номер', validators=[DataRequired()])
    representative_name = StringField('Представник компанії', validators=[DataRequired()])
    representative_email = StringField('Email представника', validators=[DataRequired(), Email()])
    document = FileField('Документи (PDF, JPG)', validators=[FileAllowed(['pdf', 'jpg', 'jpeg', 'png'])])
    submit = SubmitField('Надіслати заявку')
