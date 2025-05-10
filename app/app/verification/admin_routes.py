
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from .models import SellerVerification
from app import db

verification_admin_bp = Blueprint('verification_admin', __name__, url_prefix='/admin/verification')

@verification_admin_bp.route('/')
@login_required
def list_verifications():
    if not current_user.is_admin:
        return "Доступ заборонено", 403

    verifications = SellerVerification.query.order_by(SellerVerification.created_at.desc()).all()
    return render_template('admin/verification_list.html', verifications=verifications)

@verification_admin_bp.route('/approve/<int:verification_id>')
@login_required
def approve_verification(verification_id):
    verification = SellerVerification.query.get(verification_id)
    verification.status = "approved"
    verification.verified_at = db.func.now()
    db.session.commit()

    flash("Заявка верифікована.", "success")
    return redirect(url_for('verification_admin.list_verifications'))

@verification_admin_bp.route('/reject/<int:verification_id>')
@login_required
def reject_verification(verification_id):
    verification = SellerVerification.query.get(verification_id)
    verification.status = "rejected"
    db.session.commit()

    flash("Заявка відхилена.", "danger")
    return redirect(url_for('verification_admin.list_verifications'))
