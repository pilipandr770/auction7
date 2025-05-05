from flask import Blueprint, render_template
from flask_login import current_user
from blockchain_payments.payment_token_discount import get_user_discount
from app.models.auction import Auction

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    auctions = Auction.query.filter_by(is_active=True).all()
    discount = None
    if current_user.is_authenticated and current_user.wallet_address:
        try:
            discount = get_user_discount(current_user.wallet_address)
        except Exception:
            discount = None
    return render_template('index.html', auctions=auctions, user_discount=discount)

@main_bp.route('/privacy')
def privacy():
    return render_template('privacy.html')

@main_bp.route('/impressum')
def impressum():
    return render_template('impressum.html')

@main_bp.route('/contacts')
def contacts():
    return render_template('contacts.html')
