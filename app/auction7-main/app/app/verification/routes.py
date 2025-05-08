
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from .forms import SellerRegisterForm
from .models import SellerVerification
from app import db
import os

verification_bp = Blueprint('verification', __name__, url_prefix='/verification')
UPLOAD_FOLDER = os.path.join('app', 'static', 'verification_docs')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@verification_bp.route('/register', methods=['GET', 'POST'])
def register_seller():
    form = SellerRegisterForm()

    if form.validate_on_submit():
        document_path = None
        if form.document.data:
            filename = form.document.data.filename
            document_path = os.path.join(UPLOAD_FOLDER, filename)
            form.document.data.save(document_path)

        new_verification = SellerVerification(
            user_id=current_user.id,
            company_name=form.company_name.data,
            registration_number=form.registration_number.data,
            country=form.country.data,
            company_address=form.company_address.data,
            tax_id=form.tax_id.data,
            representative_name=form.representative_name.data,
            representative_email=form.representative_email.data,
            documents=[document_path] if document_path else [],
            status="pending"
        )
        db.session.add(new_verification)
        db.session.commit()

        flash("Заявка на верифікацію подана!", "success")
        return redirect(url_for('main.index'))

    return render_template('verification/register.html', form=form)

