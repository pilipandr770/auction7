from auction7.app import db
from datetime import datetime

class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    auction_id = db.Column(db.Integer, db.ForeignKey('auctions.id'), nullable=True)  # Може бути None для поповнення балансу
    amount = db.Column(db.Float, nullable=False)
    purpose = db.Column(db.String(50), nullable=False)  # 'entry_fee', 'view_info', 'balance_topup'
    recipient = db.Column(db.String(50), nullable=False)  # 'seller', 'platform', 'user'
    status = db.Column(db.String(20), default='pending')  # 'pending', 'completed', 'failed', 'refunded'
    
    # Stripe integration fields
    stripe_payment_intent_id = db.Column(db.String(255), nullable=True)
    stripe_session_id = db.Column(db.String(255), nullable=True)
    stripe_charge_id = db.Column(db.String(255), nullable=True)
    failure_reason = db.Column(db.Text, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    user = db.relationship('User', backref='payments')
    auction = db.relationship('Auction', backref='payments')

    def __init__(self, user_id, amount, purpose, recipient, auction_id=None, 
                 stripe_payment_intent_id=None, stripe_session_id=None, status='pending'):
        self.user_id = user_id
        self.auction_id = auction_id
        self.amount = amount
        self.purpose = purpose
        self.recipient = recipient
        self.status = status
        self.stripe_payment_intent_id = stripe_payment_intent_id
        self.stripe_session_id = stripe_session_id

    def process_payment(self):
        """Позначає платіж як оброблений."""
        self.status = 'completed'
        self.processed_at = datetime.utcnow()
        db.session.commit()
        
    def fail_payment(self, reason=None):
        """Позначає платіж як неуспішний."""
        self.status = 'failed'
        self.failure_reason = reason
        self.processed_at = datetime.utcnow()
        db.session.commit()
        
    def refund_payment(self):
        """Позначає платіж як повернений."""
        self.status = 'refunded'
        self.processed_at = datetime.utcnow()
        db.session.commit()
    
    @property
    def is_processed(self):
        """Compatibility with old code."""
        return self.status == 'completed'
    
    def get_formatted_amount(self):
        """Повертає відформатовану суму."""
        return f"${self.amount:.2f}"
    
    def get_status_display(self):
        """Повертає статус українською мовою."""
        status_map = {
            'pending': 'Очікується',
            'completed': 'Завершено',
            'failed': 'Неуспішно',
            'refunded': 'Повернено'
        }
        return status_map.get(self.status, self.status)
        
    def get_purpose_display(self):
        """Повертає призначення платежу українською мовою."""
        purpose_map = {
            'entry_fee': 'Плата за участь',
            'view_info': 'Плата за перегляд',
            'balance_topup': 'Поповнення балансу'
        }
        return purpose_map.get(self.purpose, self.purpose)
