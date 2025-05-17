from app import db

class Payment(db.Model):
    __tablename__ = 'payments'  # Додано ім'я таблиці для ясності

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Виправлено назву таблиці
    auction_id = db.Column(db.Integer, db.ForeignKey('auctions.id'), nullable=False)  # Додано ForeignKey
    amount = db.Column(db.Float, nullable=False)
    purpose = db.Column(db.String(50), nullable=False)  # Наприклад, 'entry_fee' або 'view_info'
    recipient = db.Column(db.String(50), nullable=False)  # Наприклад, 'seller' або 'platform'
    is_processed = db.Column(db.Boolean, default=False)

    def __init__(self, user_id, auction_id, amount, purpose, recipient):
        self.user_id = user_id
        self.auction_id = auction_id
        self.amount = amount
        self.purpose = purpose
        self.recipient = recipient
        self.is_processed = False

    def process_payment(self):
        """Метод для обробки платежу."""
        # У майбутньому можна додати інтеграцію з реальною платіжною системою
        self.is_processed = True
        db.session.commit()
