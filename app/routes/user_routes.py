# routes/user_routes.py

from flask import Blueprint, request, jsonify, redirect, url_for, flash, render_template
from flask_login import login_required, current_user
from app import db
from app.models.user import User
from app.models.auction import Auction  # Імпортуємо модель Auction

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

@user_bp.route('/buyer/<string:email>', methods=['GET'])
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

    # Додаємо логіку для отримання аукціонів поточного продавця
    auctions = Auction.query.filter_by(seller_id=user.id).all()

    return render_template('users/seller_dashboard.html', user=user, auctions=auctions)

@user_bp.route('/participate/<int:auction_id>', methods=['POST'])
@login_required
def participate_in_auction(auction_id):
    auction = Auction.query.get(auction_id)
    if not auction or not auction.is_active:
        return jsonify({"error": "Аукціон не знайдено або вже закритий"}), 400

    ticket_price = 10  # Фіксована вартість квитка
    if current_user.balance < ticket_price:
        return jsonify({"error": "Недостатньо коштів на балансі"}), 400

    # Списуємо гроші з балансу покупця
    current_user.balance -= ticket_price

    # Додаємо гроші на баланс продавця
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

