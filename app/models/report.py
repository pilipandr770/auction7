from datetime import datetime
from app import db


class Report(db.Model):
    """DSA Notice-and-Action — Meldung eines rechtswidrigen/unzulässigen Inserats."""
    __tablename__ = 'reports'

    id = db.Column(db.Integer, primary_key=True)
    auction_id = db.Column(db.Integer, db.ForeignKey('auctions.id'), nullable=False)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # null = anonym
    reason = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(16), default='open')  # open / reviewed / removed
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __init__(self, auction_id, reason, reporter_id=None):
        self.auction_id = auction_id
        self.reason = reason
        self.reporter_id = reporter_id
