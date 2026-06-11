from flask import Blueprint, request, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from app.models.user import User
from app import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Перевірка користувача
        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash("E-Mail oder Passwort ist falsch", 'error')
            return redirect(url_for('auth.login'))

        # Авторизація користувача
        login_user(user)
        flash("Erfolgreich angemeldet", 'success')

        # Перевірка типу користувача (user_type)
        if user.user_type == "admin":
            return redirect(url_for('admin.admin_dashboard'))  # Виправлений шлях
        elif user.user_type == "seller":
            return redirect(url_for('user.seller_dashboard', email=user.email))
        elif user.user_type == "buyer":
            return redirect(url_for('user.buyer_dashboard', email=user.email))
        else:
            flash("Benutzerrolle nicht definiert", 'error')
            return redirect(url_for('auth.login'))

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        user_type = request.form.get('user_type')  # "seller", "buyer" або "admin"

        if not email or not username or not password or not user_type:
            flash("Alle Felder sind erforderlich", 'error')
            return redirect(url_for('auth.register'))

        # Перевірка, чи email вже існує
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Ein Benutzer mit dieser E-Mail existiert bereits", 'error')
            return redirect(url_for('auth.register'))

        # Перевірка типу користувача
        if user_type not in ['buyer', 'seller', 'admin']:
            flash("Ungültiger Benutzertyp", 'error')
            return redirect(url_for('auth.register'))

        # Створення нового користувача
        user = User(username=username, email=email, password=password, user_type=user_type)
        if user_type == "admin":
            user.is_admin = True  # Позначаємо адміністратора
        db.session.add(user)
        db.session.commit()

        flash("Registrierung erfolgreich", 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth_bp.route('/logout', methods=['GET'])
def logout():
    if current_user.is_authenticated:
        logout_user()
        flash("Sie wurden erfolgreich abgemeldet", 'success')
    else:
        flash("Sie sind noch nicht angemeldet", 'error')
    return redirect(url_for('auth.login'))
