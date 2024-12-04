# models/user.py
from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin


class User(UserMixin, db.Model):
    __tablename__ = 'users'  # Додано ім'я таблиці для ясності

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(128), nullable=False)
    balance = db.Column(db.Float, default=0.0)
    user_type = db.Column(db.String(10), nullable=False)  # "buyer" або "seller"

    # Встановлення зв'язків із таблицею аукціонів
    auctions_created = db.relationship('Auction', foreign_keys='Auction.seller_id', backref='seller', lazy=True)
    auctions_won = db.relationship('Auction', foreign_keys='Auction.winner_id', backref='winner', lazy=True)

    def __init__(self, username, email, password, user_type):
        self.username = username
        self.email = email
        self.set_password(password)
        self.user_type = user_type

    def set_password(self, password):
        """Зберігає хешований пароль."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Перевіряє хеш пароля."""
        return check_password_hash(self.password_hash, password)

    # Методи для Flask-Login
    def get_id(self):
        """Повертає унікальний ідентифікатор користувача як рядок."""
        return str(self.id)
