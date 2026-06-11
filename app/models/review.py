from datetime import datetime
from app import db


class Review(db.Model):
    """Verkäuferbewertung — nur vom Gewinner einer bestätigten Auktion (verified purchase)."""
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    auction_id = db.Column(db.Integer, db.ForeignKey('auctions.id'), nullable=False)
    stars = db.Column(db.Integer, nullable=False)        # 1..5
    text = db.Column(db.String(1000), nullable=True)
    status = db.Column(db.String(16), default='approved')  # approved / flagged
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Ein Review pro Auktion
    __table_args__ = (db.UniqueConstraint('auction_id', 'reviewer_id', name='uq_review_auction_reviewer'),)

    def __init__(self, seller_id, reviewer_id, auction_id, stars, text=None, status='approved'):
        self.seller_id = seller_id
        self.reviewer_id = reviewer_id
        self.auction_id = auction_id
        self.stars = stars
        self.text = text
        self.status = status
