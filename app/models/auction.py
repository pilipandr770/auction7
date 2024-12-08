from app import db


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
    created_at = db.Column(db.DateTime, default=db.func.now(), nullable=False)
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now(), nullable=False)

    def __init__(self, title, description, starting_price, seller_id):
        self.title = title
        self.description = description
        self.starting_price = starting_price
        self.current_price = starting_price
        self.seller_id = seller_id

    def add_participant(self):
        """Метод для додавання нового учасника до аукціону."""
        self.total_participants += 1

    def decrease_price(self, entry_price):
        """Метод для зниження ціни після кожного нового учасника."""
        self.current_price -= entry_price
        if self.current_price <= 0:
            self.current_price = 0
            self.close_auction()

    def close_auction(self, winner_id=None):
        """Метод для закриття аукціону."""
        self.is_active = False
        self.winner_id = winner_id

    def get_status(self):
        """Метод для отримання статусу аукціону."""
        return 'Активний' if self.is_active else 'Закритий'

    def is_participation_allowed(self, user_balance, entry_price):
        """
        Перевіряє, чи може користувач взяти участь в аукціоні.

        :param user_balance: Баланс користувача
        :param entry_price: Ціна за участь
        :return: True, якщо участь можлива, False - якщо ні
        """
        if not self.is_active:
            return False
        if user_balance < entry_price:
            return False
        return True

    def get_time_info(self):
        """
        Повертає інформацію про час створення і оновлення аукціону.

        :return: Словник з датами створення та останнього оновлення
        """
        return {
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }

    def reset_current_price(self):
        """
        Скидає поточну ціну до стартової ціни.
        """
        self.current_price = self.starting_price
