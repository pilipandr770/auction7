from datetime import datetime
from app import db


class Transaction(db.Model):
    """Леджер усіх грошових операцій — аудит та ідемпотентність.

    Типи (type):
      topup_credits   — покупка сервіс-кредитів (дохід платформи)
      view_fee        — списання кредиту за перегляд ціни
      entry_fee       — вхід в аукціон (off-session, ескроу)
      closing_payment — закриття аукціону (off-session, ескроу)
      transfer_seller — виплата продавцю з ескроу (Connect transfer)
      refund          — повернення
    """
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    auction_id = db.Column(db.Integer, db.ForeignKey('auctions.id'), nullable=True)

    type = db.Column(db.String(32), nullable=False)
    amount_eur = db.Column(db.Float, default=0.0)        # сума в EUR (де застосовно)
    credits_delta = db.Column(db.Integer, default=0)     # зміна балансу кредитів (де застосовно)
    currency = db.Column(db.String(8), default='eur')

    # Stripe-ідентифікатор (PaymentIntent / Checkout Session / Transfer) — для ідемпотентності
    stripe_id = db.Column(db.String(80), nullable=True, unique=True)
    status = db.Column(db.String(24), default='pending')  # pending / succeeded / failed

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __init__(self, type, user_id=None, auction_id=None, amount_eur=0.0,
                 credits_delta=0, stripe_id=None, status='pending', currency='eur'):
        self.type = type
        self.user_id = user_id
        self.auction_id = auction_id
        self.amount_eur = amount_eur
        self.credits_delta = credits_delta
        self.stripe_id = stripe_id
        self.status = status
        self.currency = currency
