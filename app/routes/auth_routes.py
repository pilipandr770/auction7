# routes/auth_routes.py
from flask import Blueprint, request, jsonify, render_template, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from app.models.user import User
from app import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        # Вказуємо правильний шлях до шаблону
        return render_template('auth/register.html')

    data = request.get_json() if request.is_json else request.form
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    user_type = data.get('user_type')  # Тип користувача: buyer або seller

    if not user_type or user_type not in ['buyer', 'seller']:
        return render_template('auth/register.html', error="Невірний тип користувача. Має бути 'buyer' або 'seller'")

    if User.query.filter_by(email=email).first() is not None:
        return render_template('auth/register.html', error="Користувач із такою електронною адресою вже існує")

    hashed_password = generate_password_hash(password)
    new_user = User(username=username, email=email, password=hashed_password, user_type=user_type)
    db.session.add(new_user)
    db.session.commit()
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        # Вказуємо правильний шлях до шаблону
        return render_template('auth/login.html')

    data = request.get_json() if request.is_json else request.form
    email = data.get('email')
    password = data.get('password')

    # Знайти користувача в базі даних за електронною поштою
    user = User.query.filter_by(email=email).first()

    if user and user.check_password(password):
        # Якщо все вірно, перенаправляємо залежно від типу користувача
        if user.user_type == 'buyer':
            return render_template('users/buyer_dashboard.html', user=user)
        else:
            return render_template('users/seller_dashboard.html', user=user)

    return render_template('auth/login.html', error="Неправильний email або пароль"), 401


@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    # Простий маршрут для імітації виходу
    return redirect(url_for('auth.login'))
