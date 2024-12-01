# routes/user_routes.py
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from app import db
from app.services.payment_service import PaymentService
from app.models.user import User

user_bp = Blueprint('user', __name__)

@user_bp.route('/add_balance', methods=['POST'])
@login_required
def add_balance():
    data = request.get_json()
    if not data:
        return jsonify({"message": "Необхідний формат запиту JSON"}), 400

    user_email = current_user.email  # Використовуємо email поточного користувача
    amount = data.get('amount')

    response, status_code = PaymentService.add_balance(user_email, amount)
    return jsonify(response), status_code

@user_bp.route('/buyer/<string:email>', methods=['GET'])
@login_required
def buyer_dashboard(email):
    if current_user.email != email:
        return jsonify({"message": "Неавторизований доступ"}), 403

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"message": "Користувача не знайдено"}), 404

    return jsonify({
        "username": user.username,
        "email": user.email,
        "balance": user.balance,
        "role": "buyer"
    }), 200

@user_bp.route('/seller/<string:email>', methods=['GET'])
@login_required
def seller_dashboard(email):
    if current_user.email != email:
        return jsonify({"message": "Неавторизований доступ"}), 403

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"message": "Користувача не знайдено"}), 404

    return jsonify({
        "username": user.username,
        "email": user.email,
        "balance": user.balance,
        "role": "seller"
    }), 200

@user_bp.route('/update_profile/<string:email>', methods=['PUT'])
@login_required
def update_profile(email):
    if current_user.email != email:
        return jsonify({"message": "Неавторизований доступ"}), 403

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"message": "Користувача не знайдено"}), 404

    data = request.get_json()
    username = data.get('username')
    new_password = data.get('password')

    if username:
        user.username = username
    if new_password:
        user.password_hash = generate_password_hash(new_password)

    # Зберігаємо зміни в базі даних
    db.session.commit()

    return jsonify({"message": "Профіль успішно оновлено"}), 200
