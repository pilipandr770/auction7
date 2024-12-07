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
        flash("Тільки продавці можуть створювати аукціони.", "error")
        return redirect(url_for('user.seller_dashboard', email=current_user.email))

    data = request.form
    title = data.get('title')
    description = data.get('description')
    starting_price = data.get('starting_price')

    if not title or not description or not starting_price:
        flash("Усі поля обов'язкові.", "error")
        return redirect(url_for('user.seller_dashboard', email=current_user.email))

    try:
        starting_price = float(starting_price)
    except ValueError:
        flash("Ціна повинна бути числом.", "error")
        return redirect(url_for('user.seller_dashboard', email=current_user.email))

    new_auction = Auction(
        title=title,
        description=description,
        starting_price=starting_price,
        current_price=starting_price,
        seller_id=current_user.id
    )

    db.session.add(new_auction)
    db.session.commit()

    flash("Аукціон успішно створено!", "success")
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

@auction_bp.route('/<int:auction_id>', methods=['GET', 'POST'])
@login_required
def auction_detail(auction_id):
    auction = Auction.query.get(auction_id)

    if not auction:
        flash("Аукціон не знайдено.", 'error')
        return redirect(url_for('auction.buyer_auctions'))

    if request.method == 'POST':
        entry_price = auction.starting_price * 0.1  # Вхідна ціна (10% від початкової ціни)
        buyer = User.query.get(current_user.id)
        seller = User.query.get(auction.seller_id)

        if buyer.balance < entry_price:
            flash("Недостатньо коштів на балансі для участі в аукціоні.", 'error')
            return redirect(url_for('auction.auction_detail', auction_id=auction_id))

        # Списуємо з балансу покупця і додаємо на баланс продавця
        buyer.balance -= entry_price
        seller.balance += entry_price
        auction.total_participants += 1

        # Зменшуємо поточну ціну
        auction.current_price -= entry_price
        if auction.current_price <= 0:
            auction.current_price = 0
            auction.is_active = False  # Закриваємо аукціон

        db.session.commit()

        flash(f"Ви успішно взяли участь в аукціоні. Учасників: {auction.total_participants}", 'success')
        return redirect(url_for('auction.auction_detail', auction_id=auction_id))

    return render_template('auctions/auction_detail.html', auction=auction)
