from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy.orm import validates

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(128), nullable=False)
    balance = db.Column(db.Float, default=0.0)
    user_type = db.Column(db.String(10), nullable=False)  # "buyer", "seller", "admin"
    is_admin = db.Column(db.Boolean, default=False)  # Поле для адміністратора

    # Зв'язки
    auctions_created = db.relationship('Auction', foreign_keys='Auction.seller_id', backref='seller', lazy=True)
    auctions_won = db.relationship('Auction', foreign_keys='Auction.winner_id', backref='winner', lazy=True)
    auction_participations = db.relationship('AuctionParticipant', back_populates='user', lazy=True)

    def __init__(self, username, email, password, user_type, is_admin=False):
        self.username = username
        self.email = email
        self.set_password(password)
        if user_type not in ['buyer', 'seller', 'admin']:
            raise ValueError("Неприпустимий тип користувача")
        self.user_type = user_type
        self.is_admin = is_admin

    def set_password(self, password):
        """Зберігає хешований пароль."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Перевіряє хеш пароля."""
        return check_password_hash(self.password_hash, password)

    def can_afford(self, amount):
        """
        Перевіряє, чи вистачає коштів на балансі для певної операції.
        :param amount: Сума для перевірки.
        :return: True, якщо вистачає, False - якщо ні.
        """
        return self.balance >= amount

    def deduct_balance(self, amount):
        """
        Віднімає певну суму з балансу користувача.
        :param amount: Сума для віднімання.
        """
        if self.can_afford(amount):
            print(f"[INFO] Баланс до списання: {self.balance}")  # Діагностика
            self.balance -= amount
            db.session.commit()
            print(f"[INFO] Баланс після списання: {self.balance}")  # Діагностика
        else:
            raise ValueError("Недостатньо коштів на балансі.")

    def add_balance(self, amount):
        """
        Додає кошти до балансу користувача.
        :param amount: Сума для додавання.
        """
        if amount > 0:
            print(f"[INFO] Баланс до поповнення: {self.balance}")  # Діагностика
            self.balance += amount
            db.session.commit()
            print(f"[INFO] Баланс після поповнення: {self.balance}")  # Діагностика
        else:
            raise ValueError("Сума для поповнення повинна бути більше нуля.")

    @validates('user_type')
    def validate_user_type(self, key, value):
        """Перевіряє правильність типу користувача."""
        if value not in ['buyer', 'seller', 'admin']:
            raise ValueError("Неприпустимий тип користувача")
        return value
