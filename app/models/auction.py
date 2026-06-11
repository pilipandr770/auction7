from datetime import datetime, timedelta
from sqlalchemy.orm import relationship
from app.models.auction_participant import AuctionParticipant
from app import db
from sqlalchemy.dialects.sqlite import JSON

# Тривалість вікна заморозки нових входів (секунди)
FREEZE_SECONDS = 5


class Auction(db.Model):
    __tablename__ = 'auctions'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    starting_price = db.Column(db.Float, nullable=False)
    current_price = db.Column(db.Float, nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    total_participants = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    winner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    total_earnings = db.Column(db.Float, default=0.0, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now(), nullable=False)
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now(), nullable=False)
    photos = db.Column(JSON, default=list)  # Поле для зберігання шляхів до фото у форматі JSON
    is_confirmed = db.Column(db.Boolean, default=False, nullable=False)  # Чи підтверджено отримання товару
    frozen_until = db.Column(db.DateTime, nullable=True)  # Вікно заморозки нових входів (5 сек)
    market_reference = db.Column(db.String(500), nullable=True)  # Посилання на ринкову ціну (для перевірки)
    moderation_status = db.Column(db.String(16), default='approved')  # approved/flagged/rejected/pending
    moderation_reason = db.Column(db.String(500), nullable=True)  # Причина флагу/відхилення (AI)
    seller_confirmed = db.Column(db.Boolean, default=False)  # Продавець підтвердив справжність лоту

    # Відношення з AuctionParticipant
    participants = relationship(
        'AuctionParticipant', back_populates='auction', cascade='all, delete-orphan', lazy='dynamic'
    )

    def __init__(self, title, description, starting_price, seller_id, photos=None, market_reference=None):
        self.title = title
        self.description = description
        self.starting_price = starting_price
        self.current_price = starting_price
        self.seller_id = seller_id
        self.photos = photos if photos else []
        self.market_reference = market_reference

    def freeze(self):
        """Заморожує нові входи на FREEZE_SECONDS секунд (після входу/перегляду)."""
        self.frozen_until = datetime.utcnow() + timedelta(seconds=FREEZE_SECONDS)

    def is_frozen(self):
        """Чи активне вікно заморозки нових входів."""
        return self.frozen_until is not None and datetime.utcnow() < self.frozen_until

    def freeze_seconds_left(self):
        """Скільки секунд залишилось до кінця заморозки (0 якщо не заморожено)."""
        if not self.is_frozen():
            return 0
        return max(0, int((self.frozen_until - datetime.utcnow()).total_seconds()) + 1)

    def add_participant(self, user):
        if not self.is_user_participant(user):
            new_participant = AuctionParticipant(auction_id=self.id, user_id=user.id)
            db.session.add(new_participant)
            self.total_participants += 1

    def is_user_participant(self, user):
        return self.participants.filter_by(user_id=user.id).count() > 0

    def decrease_price(self, entry_price):
        """
        Зменшує поточну ціну аукціону на задану суму.
        """
        self.current_price -= entry_price
        if self.current_price <= 0:
            self.current_price = 0
            self.close_auction()

    def close_auction(self, winner_id=None):
        """
        Закриває аукціон, встановлюючи статус як неактивний,
        та зберігає ID переможця, якщо вказано.
        """
        self.is_active = False
        if winner_id:
            self.winner_id = winner_id
        db.session.commit()

    def finalize_auction(self, buyer, seller):
        """
        Завершує аукціон:
        - Списує кошти з переможця (лише `current_price`).
        - Додає дохід до балансу продавця (всі вхідні внески + `current_price`).
        - Зберігає ID переможця.
        - Закриває аукціон.
        """
        # Розрахунок загального доходу продавця
        total_entry_payments = self.total_participants * self.starting_price * 0.01
        total_revenue = total_entry_payments + self.current_price

        # Перевірка, чи вистачає коштів у покупця
        if buyer.balance < self.current_price:
            raise ValueError("Nicht genügend Guthaben zum Abschluss der Auktion.")

        # Списуємо тільки `current_price` з покупця
        buyer.deduct_balance(self.current_price)

        # Додаємо всю зароблену суму до балансу продавця
        seller.add_balance(total_revenue)

        # Закриваємо аукціон
        self.close_auction(winner_id=buyer.id)

    def add_to_earnings(self, amount):
        """
        Додає суму до заробітку аукціону.
        """
        self.total_earnings += amount
        db.session.commit()

    def charge_for_view(self, user, amount):
        """
        Списує суму з користувача за перегляд поточної ціни
        та додає її до заробітку аукціону.
        """
        if user.can_afford(amount):
            user.deduct_balance(amount)
            self.add_to_earnings(amount)
        else:
            raise ValueError("Nicht genügend Guthaben für die Preis-Einsicht.")

    def get_status(self):
        """
        Повертає статус аукціону як рядок ('Активний' або 'Закритий').
        """
        return 'Aktiv' if self.is_active else 'Beendet'

    def is_participation_allowed(self, user_balance, entry_price):
        """
        Перевіряє, чи дозволено користувачу брати участь в аукціоні.
        """
        if not self.is_active or user_balance < entry_price:
            return False
        return True

    def get_time_info(self):
        """
        Повертає інформацію про час створення та оновлення аукціону.
        """
        return {
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }

    def reset_current_price(self):
        """
        Скидає поточну ціну до стартової.
        """
        self.current_price = self.starting_price

    def add_photos(self, photos):
        """
        Додає шляхи до фотографій у поле photos.
        :param photos: Список шляхів до фотографій.
        """
        if not self.photos:
            self.photos = []
        self.photos.extend(photos)
        db.session.commit()
