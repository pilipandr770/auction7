from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models.auction import Auction
from app.models.user import User

auction_bp = Blueprint('auction', __name__)

@auction_bp.route('/create', methods=['POST'])
@login_required
def create_auction():
    if current_user.user_type != 'seller':
        return jsonify({"error": "Тільки продавці можуть створювати аукціони"}), 403

    data = request.form
    title = data.get('title')
    description = data.get('description')
    starting_price = data.get('starting_price')

    if not title or not description or not starting_price:
        return jsonify({"error": "Усі поля обов'язкові"}), 400

    try:
        starting_price = float(starting_price)
    except ValueError:
        return jsonify({"error": "Ціна повинна бути числом"}), 400

    new_auction = Auction(
        title=title,
        description=description,
        starting_price=starting_price,
        seller_id=current_user.id
    )

    db.session.add(new_auction)
    db.session.commit()

    flash("Аукціон успішно створено", "success")
    return redirect(url_for('user.seller_dashboard', email=current_user.email))

@auction_bp.route('/list', methods=['GET'])
def list_auctions():
    auctions = Auction.query.filter_by(is_active=True).all()
    return render_template('index.html', auctions=auctions)

@auction_bp.route('/seller', methods=['GET'])
@login_required
def seller_auctions():
    if current_user.user_type != 'seller':
        return redirect(url_for('auth.login'))

    auctions = Auction.query.filter_by(seller_id=current_user.id).all()
    return render_template('users/seller_dashboard.html', auctions=auctions)

@auction_bp.route('/buyer', methods=['GET'])
@login_required
def buyer_auctions():
    if current_user.user_type != 'buyer':
        return redirect(url_for('auth.login'))

    auctions = Auction.query.filter_by(is_active=True).all()
    return render_template('users/buyer_dashboard.html', auctions=auctions)
