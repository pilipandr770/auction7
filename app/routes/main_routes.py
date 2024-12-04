from flask import Blueprint, render_template
from app.models.auction import Auction

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    auctions = Auction.query.filter_by(is_active=True).all()
    return render_template('index.html', auctions=auctions)
