# models/payment.py
from app import db

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    auction_id = db.Column(db.Integer, nullable=False)  # Можна створити ForeignKey, якщо є відповідна модель аукціону
    amount = db.Column(db.Float, nullable=False)
    purpose = db.Column(db.String(50), nullable=False)  # Може бути 'entry_fee' або 'view_info'
    recipient = db.Column(db.String(50), nullable=False)  # Може бути 'seller' або 'platform'
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
        # В майбутньому тут можна додати логіку інтеграції з реальною платіжною системою
        self.is_processed = True
        db.session.commit()
