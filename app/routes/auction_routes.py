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

    try:
        new_auction = Auction(
            title=title,
            description=description,
            starting_price=starting_price,
            seller_id=current_user.id
        )
        db.session.add(new_auction)
        db.session.commit()

        flash("Аукціон успішно створено!", "success")
    except Exception as e:
        db.session.rollback()
        print(f"Помилка створення аукціону: {e}")
        flash("Не вдалося створити аукціон. Спробуйте пізніше.", "error")

    return redirect(url_for('user.seller_dashboard', email=current_user.email))


@auction_bp.route('/<int:auction_id>', methods=['GET', 'POST'])
@login_required
def auction_detail(auction_id):
    auction = Auction.query.get(auction_id)

    if not auction:
        flash("Аукціон не знайдено.", 'error')
        return redirect(url_for('auction.buyer_auctions'))

    if request.method == 'POST':
        try:
            entry_price = auction.starting_price * 0.1  # Вхідна ціна (10% від початкової ціни)
            buyer = User.query.get(current_user.id)

            if not buyer:
                return jsonify({"error": "Користувача не знайдено"}), 404

            if buyer.balance < entry_price:
                return jsonify({"error": "Недостатньо коштів на балансі"}), 400

            # Оновлення даних аукціону
            buyer.balance -= entry_price
            seller = User.query.get(auction.seller_id)

            if seller:
                seller.balance += entry_price

            auction.total_participants += 1
            auction.current_price -= entry_price

            if auction.current_price <= 0:
                auction.current_price = 0
                auction.is_active = False  # Закриваємо аукціон

            db.session.commit()

            return jsonify({
                "message": "Успішно взято участь в аукціоні",
                "participants": auction.total_participants,
                "final_price": auction.current_price
            }), 200

        except Exception as e:
            db.session.rollback()
            print(f"Помилка участі в аукціоні: {e}")
            return jsonify({"error": "Не вдалося взяти участь в аукціоні"}), 500

    return render_template('auctions/auction_detail.html', auction=auction)


@auction_bp.route('/participate/<int:auction_id>', methods=['POST'])
@login_required
def participate_in_auction(auction_id):
    auction = Auction.query.get(auction_id)
    if not auction:
        return jsonify({"error": "Аукціон не знайдено"}), 404

    if not auction.is_active:
        return jsonify({"error": "Аукціон вже закритий"}), 400

    ticket_price = auction.starting_price * 0.1
    try:
        if current_user.balance < ticket_price:
            return jsonify({"error": "Недостатньо коштів на балансі"}), 400

        seller = User.query.get(auction.seller_id)
        if not seller:
            return jsonify({"error": "Продавця не знайдено"}), 404

        current_user.balance -= ticket_price
        seller.balance += ticket_price

        auction.total_participants += 1
        auction.current_price -= ticket_price

        if auction.current_price <= 0:
            auction.current_price = 0
            auction.is_active = False

        db.session.commit()

        return jsonify({
            "message": "Успішно взято участь!",
            "participants": auction.total_participants,
            "final_price": auction.current_price
        }), 200
    except Exception as e:
        db.session.rollback()
        print(f"Помилка участі в аукціоні: {e}")
        return jsonify({"error": "Не вдалося взяти участь в аукціоні"}), 500
