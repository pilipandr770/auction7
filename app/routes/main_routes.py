from flask import Blueprint, render_template, abort
from flask_login import current_user
from blockchain_payments.payment_token_discount import get_user_discount
from app.models.auction import Auction
from app.models.user import User
from app.models.review import Review

main_bp = Blueprint('main', __name__)


@main_bp.route('/seller/<int:seller_id>')
def seller_profile(seller_id):
    """Öffentliches Verkäuferprofil mit Bewertungen (Preis/Teilnehmer bleiben geheim)."""
    seller = User.query.get(seller_id)
    if not seller or seller.user_type != 'seller' or seller.is_deleted:
        abort(404)
    reviews = (Review.query.filter_by(seller_id=seller_id, status='approved')
               .order_by(Review.created_at.desc()).all())
    active_auctions = Auction.query.filter_by(seller_id=seller_id, is_active=True).all()
    sold_count = Auction.query.filter_by(seller_id=seller_id, is_active=False, is_confirmed=True).count()
    return render_template('seller_profile.html', seller=seller, reviews=reviews,
                           active_auctions=active_auctions, sold_count=sold_count)

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

@main_bp.route('/hilfe')
def guide():
    return render_template('guide.html')


@main_bp.route('/privacy')
def privacy():
    return render_template('privacy.html')

@main_bp.route('/impressum')
def impressum():
    return render_template('impressum.html')

@main_bp.route('/contacts')
def contacts():
    return render_template('contacts.html')
