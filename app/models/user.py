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
    platform_balance = db.Column(db.Float, default=0.0)  # Баланс платформи
    user_type = db.Column(db.String(10), nullable=False)  # "buyer", "seller", "admin"
    is_admin = db.Column(db.Boolean, default=False)  # Поле для адміністратора
    wallet_address = db.Column(db.String(42), nullable=True)  # Адреса криптогаманця

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

    def add_platform_balance(self, amount):
        """
        Додає кошти до балансу платформи (адміністратора).
        :param amount: Сума для додавання.
        """
        if amount > 0:
            print(f"[INFO] Баланс платформи до поповнення: {self.platform_balance}")  # Діагностика
            self.platform_balance += amount
            db.session.commit()
            print(f"[INFO] Баланс платформи після поповнення: {self.platform_balance}")  # Діагностика
        else:
            raise ValueError("Сума для поповнення повинна бути більше нуля.")

    def process_auction_closure(self, auction, buyer):
        """
        Завершує аукціон:
        - Списує кошти з балансу покупця.
        - Додає кошти на баланс продавця.
        - Оновлює дані аукціону.
        - Генерує повідомлення для покупця та продавця.
        """
        if not auction.is_active:
            raise ValueError("Аукціон вже закритий.")
        if buyer.balance < auction.current_price:
            raise ValueError("Недостатньо коштів для закриття аукціону.")

        # Списуємо кошти з балансу покупця
        buyer.deduct_balance(auction.current_price)

        # Додаємо кошти на баланс продавця
        self.add_balance(auction.current_price)

        # Завершуємо аукціон
        auction.close_auction(winner_id=buyer.id)
        db.session.commit()

        # Генеруємо повідомлення для продавця
        seller_message = f"Ваш аукціон '{auction.title}' був закритий. Переможець: {buyer.username}, Email: {buyer.email}."
        print(f"[INFO] Повідомлення продавцю: {seller_message}")

        # Генеруємо повідомлення для покупця
        buyer_message = f"Ви виграли аукціон '{auction.title}'. Продавець: {self.username}, Email: {self.email}."
        print(f"[INFO] Повідомлення покупцю: {buyer_message}")

    @validates('user_type')
    def validate_user_type(self, key, value):
        """Перевіряє правильність типу користувача."""
        if value not in ['buyer', 'seller', 'admin']:
            raise ValueError("Неприпустимий тип користувача")
        return value
