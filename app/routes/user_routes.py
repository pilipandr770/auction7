# routes/user_routes.py

from flask import Blueprint, request, jsonify, redirect, url_for, flash, render_template
from flask_login import login_required, current_user
from app import db
from app.models.user import User
from app.models.auction import Auction  # Імпортуємо модель Auction
from app.models.auction_participant import AuctionParticipant


user_bp = Blueprint('user', __name__)

@user_bp.route('/add_balance', methods=['POST'])
@login_required
def add_balance():
    print(f"Поточний користувач: {current_user.email}")  # Діагностика автентифікації
    data = request.get_json()

    if not data or 'amount' not in data:
        return jsonify({"error": "Некоректний формат запиту"}), 400

    try:
        amount = float(data['amount'])
        if amount <= 0:
            return jsonify({"error": "Сума має бути більше 0"}), 400

        user = User.query.filter_by(email=current_user.email).first()
        if not user:
            return jsonify({"error": "Користувача не знайдено"}), 404

        user.balance += amount
        db.session.commit()

        return jsonify({"message": "Баланс успішно поповнено!", "new_balance": user.balance}), 200
    except ValueError:
        return jsonify({"error": "Некоректна сума"}), 400
    except Exception as e:
        print(f"Помилка: {e}")
        return jsonify({"error": "Не вдалося поповнити баланс."}), 500

@user_bp.route('/buyer/<string:email>', methods=['GET', 'POST'])
@login_required
def buyer_dashboard(email):
    if current_user.email != email:
        flash("Неавторизований доступ", 'error')
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash("Користувача не знайдено", 'error')
        return redirect(url_for('auth.login'))

    auctions = Auction.query.filter_by(is_active=True).all()  # Доступні аукціони

    if request.method == 'POST':
        auction_id = request.form.get('auction_id')
        auction = Auction.query.get(auction_id)

        if not auction:
            flash("Аукціон не знайдено.", "error")
            return redirect(url_for('user.buyer_dashboard', email=current_user.email))

        try:
            view_price = 1.0  # Вартість перегляду
            participant = AuctionParticipant.query.filter_by(auction_id=auction.id, user_id=current_user.id).first()

            if participant and participant.has_viewed_price:
                flash("Ви вже переглядали поточну ціну цього аукціону.", "info")
                return redirect(url_for('user.buyer_dashboard', email=current_user.email))

            if current_user.balance < view_price:
                flash("Недостатньо коштів на балансі для перегляду ціни.", "error")
                return redirect(url_for('user.buyer_dashboard', email=current_user.email))

            # Транзакція перегляду
            current_user.balance -= view_price
            auction.add_to_earnings(view_price)

            if not participant:
                participant = AuctionParticipant(auction_id=auction.id, user_id=current_user.id)
                db.session.add(participant)

            participant.mark_viewed_price()

            db.session.commit()

            flash(f"Перегляд ціни успішний! Поточна ціна: {auction.current_price} грн", "success")
        except Exception as e:
            db.session.rollback()
            print(f"Помилка перегляду ціни: {e}")
            flash("Не вдалося виконати перегляд. Спробуйте пізніше.", "error")

    return render_template('users/buyer_dashboard.html', user=user, auctions=auctions)


@user_bp.route('/seller/<string:email>', methods=['GET'])
@login_required
def seller_dashboard(email):
    if current_user.email != email:
        flash("Неавторизований доступ", 'error')
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash("Користувача не знайдено", 'error')
        return redirect(url_for('auth.login'))

    # Отримуємо всі аукціони продавця
    all_auctions = Auction.query.filter_by(seller_id=user.id).all()

    # Фільтруємо завершені аукціони
    completed_auctions = [
        {
            'title': auction.title,
            'description': auction.description,
            'starting_price': auction.starting_price,
            'status': 'Закритий' if not auction.is_active else 'Активний',
            'total_earnings': round(auction.starting_price + auction.current_price, 2),
            'total_participants': auction.total_participants
        }
        for auction in all_auctions if not auction.is_active
    ]

    # Розрахунок балансу на основі завершених аукціонів
    balance_from_completed = sum(
        auction['starting_price'] * 0.1 * auction['total_participants'] for auction in completed_auctions
    )

    return render_template(
        'users/seller_dashboard.html',
        user=user,
        auctions=completed_auctions,
        balance_from_completed=balance_from_completed
    )


@user_bp.route('/participate/<int:auction_id>', methods=['POST'])
@login_required
def participate_in_auction(auction_id):
    auction = Auction.query.get(auction_id)
    if not auction or not auction.is_active:
        return jsonify({"error": "Аукціон не знайдено або вже закритий"}), 400

    # Розрахунок вхідної ціни
    entry_price = auction.starting_price * 0.01
    if current_user.balance < entry_price:
        return jsonify({"error": "Недостатньо коштів на балансі"}), 400

    try:
        # Списуємо гроші з покупця
        current_user.deduct_balance(entry_price)

        # Додаємо учасника до аукціону
        participant = AuctionParticipant.query.filter_by(auction_id=auction.id, user_id=current_user.id).first()
        if not participant:
            participant = AuctionParticipant(auction_id=auction.id, user_id=current_user.id)
            db.session.add(participant)

        # Позначаємо оплату участі
        participant.has_paid_entry = True

        # Оновлюємо дані аукціону
        auction.total_participants += 1

        db.session.commit()
        return jsonify({
            "message": "Успішно взято участь!",
            "participants": auction.total_participants,
            "final_price": auction.current_price
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Помилка участі: {e}")
        return jsonify({"error": "Не вдалося взяти участь"}), 500



@user_bp.route('/close_auction/<int:auction_id>', methods=['POST'])
@login_required
def close_auction(auction_id):
    auction = Auction.query.get(auction_id)
    if not auction:
        flash("Аукціон не знайдено.", "error")
        return redirect(url_for('user.buyer_dashboard', email=current_user.email))

    if not auction.is_active:
        flash("Аукціон вже закритий.", "info")
        return redirect(url_for('user.buyer_dashboard', email=current_user.email))

    # Перевірка, чи користувач є учасником аукціону
    participant = AuctionParticipant.query.filter_by(auction_id=auction.id, user_id=current_user.id).first()
    if not participant or not participant.has_paid_entry:
        flash("Ви не можете закрити цей аукціон, оскільки не брали участь у ньому.", "error")
        return redirect(url_for('user.buyer_dashboard', email=current_user.email))

    # Перевірка, чи вистачає коштів для завершення аукціону
    if current_user.balance < auction.current_price:
        flash("Недостатньо коштів для закриття аукціону.", "error")
        return redirect(url_for('user.buyer_dashboard', email=current_user.email))

    try:
        seller = User.query.get(auction.seller_id)

        # Розрахунок загальної суми для продавця
        total_entry_payments = auction.total_participants * auction.starting_price * 0.01  # Усі вхідні внески
        total_revenue = total_entry_payments + auction.current_price  # Усі внески + остаточна ціна

        # Списуємо тільки необхідну суму (остаточну ціну) з покупця
        current_user.deduct_balance(auction.current_price)

        # Додаємо всю зароблену суму на баланс продавця
        seller.add_balance(total_revenue)

        # Закриваємо аукціон
        auction.close_auction(winner_id=current_user.id)

        db.session.commit()

        flash("Аукціон успішно закрито. Зв'яжіться з продавцем для отримання товару.", "success")
        return redirect(url_for('user.buyer_dashboard', email=current_user.email))

    except Exception as e:
        db.session.rollback()
        print(f"Помилка закриття аукціону: {e}")
        flash("Не вдалося закрити аукціон. Спробуйте пізніше.", "error")
        return redirect(url_for('user.buyer_dashboard', email=current_user.email))
