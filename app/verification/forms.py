
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Email
from flask_wtf.file import FileField, FileAllowed

class SellerRegisterForm(FlaskForm):
    company_name = StringField('Firmenname', validators=[DataRequired()])
    registration_number = StringField('Registernummer', validators=[DataRequired()])
    country = StringField('Land der Registrierung', validators=[DataRequired()])
    company_address = StringField('Firmenadresse', validators=[DataRequired()])
    tax_id = StringField('Steuernummer (USt-IdNr.)', validators=[DataRequired()])
    representative_name = StringField('Vertreter des Unternehmens', validators=[DataRequired()])
    representative_email = StringField('E-Mail des Vertreters', validators=[DataRequired(), Email()])
    document = FileField('Dokumente (PDF, JPG)', validators=[FileAllowed(['pdf', 'jpg', 'jpeg', 'png'])])
    submit = SubmitField('Antrag senden')
