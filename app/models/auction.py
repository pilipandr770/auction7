from sqlalchemy.orm import relationship
from app.models.auction_participant import AuctionParticipant
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
    total_earnings = db.Column(db.Float, default=0.0, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now(), nullable=False)
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now(), nullable=False)

    # Відношення з AuctionParticipant
    participants = relationship('AuctionParticipant', back_populates='auction', cascade='all, delete-orphan', lazy='dynamic')

    def __init__(self, title, description, starting_price, seller_id):
        self.title = title
        self.description = description
        self.starting_price = starting_price
        self.current_price = starting_price
        self.seller_id = seller_id

    def add_participant(self, user):
        if not self.is_user_participant(user):
            new_participant = AuctionParticipant(auction_id=self.id, user_id=user.id)
            db.session.add(new_participant)
            self.total_participants += 1

    def is_user_participant(self, user):
        return self.participants.filter_by(user_id=user.id).count() > 0

    def decrease_price(self, entry_price):
        self.current_price -= entry_price
        if self.current_price <= 0:
            self.current_price = 0
            self.close_auction()

    def close_auction(self, winner_id=None):
        self.is_active = False
        self.winner_id = winner_id

    def add_to_earnings(self, amount):
        self.total_earnings += amount
        db.session.commit()  # Збереження змін


    def charge_for_view(self, user, amount):
        """
        Списує суму з користувача за перегляд поточної ціни
        та додає її до заробітку аукціону.
        """
        if user.can_afford(amount):
            user.deduct_balance(amount)
            self.add_to_earnings(amount)
        else:
            raise ValueError("Недостатньо коштів для перегляду ціни.")

    def get_status(self):
        return 'Активний' if self.is_active else 'Закритий'

    def is_participation_allowed(self, user_balance, entry_price):
        if not self.is_active or user_balance < entry_price:
            return False
        return True

    def get_time_info(self):
        return {
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }

    def reset_current_price(self):
        self.current_price = self.starting_price
