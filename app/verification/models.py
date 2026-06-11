
from app import db
from datetime import datetime
from sqlalchemy.dialects.sqlite import JSON

class SellerVerification(db.Model):
    __tablename__ = 'seller_verifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    company_name = db.Column(db.String(255), nullable=False)
    registration_number = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(100), nullable=False)
    company_address = db.Column(db.String(255), nullable=False)
    tax_id = db.Column(db.String(100), nullable=False)
    representative_name = db.Column(db.String(100), nullable=False)
    representative_email = db.Column(db.String(120), nullable=False)
    documents = db.Column(JSON, nullable=True, default=list)
    status = db.Column(db.String(20), nullable=False, default="pending")
    admin_comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    verified_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", backref="seller_verification")
