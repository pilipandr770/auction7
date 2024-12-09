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
    completed_auctions = [auction for auction in all_auctions if not auction.is_active]

    # Розрахунок балансу на основі завершених аукціонів
    balance_from_completed = sum(
        auction.starting_price * 0.1 * auction.total_participants for auction in completed_auctions
    )

    return render_template(
        'users/seller_dashboard.html',
        user=user,
        auctions=all_auctions,
        balance_from_completed=balance_from_completed
    )

@user_bp.route('/participate/<int:auction_id>', methods=['POST'])
@login_required
def participate_in_auction(auction_id):
    auction = Auction.query.get(auction_id)
    if not auction or not auction.is_active:
        return jsonify({"error": "Аукціон не знайдено або вже закритий"}), 400

    # Розраховуємо вхідну ціну як 10% від початкової ціни
    ticket_price = auction.starting_price * 0.1
    if current_user.balance < ticket_price:
        return jsonify({"error": "Недостатньо коштів на балансі"}), 400

    # Списуємо гроші з балансу покупця
    current_user.balance -= ticket_price

    # Додаємо гроші на баланс продавця (але не відображаємо їх до завершення аукціону)
    seller = User.query.get(auction.seller_id)
    if seller:
        seller.balance += ticket_price

    # Збільшуємо кількість учасників
    auction.total_participants += 1

    # Оновлюємо поточну ціну
    auction.current_price -= ticket_price
    if auction.current_price <= 0:
        auction.current_price = 0
        auction.is_active = False  # Закриваємо аукціон

    db.session.commit()

    # Повертаємо інформацію для 5-секундного перегляду
    return jsonify({
        "message": "Успішно взято участь!",
        "participants": auction.total_participants,
        "final_price": auction.current_price
    }), 200
