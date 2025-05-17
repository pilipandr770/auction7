from app import db

class AuctionParticipant(db.Model):
    """
    Модель для зберігання інформації про участь користувачів в аукціонах.
    """
    __tablename__ = 'auction_participants'

    id = db.Column(db.Integer, primary_key=True)
    auction_id = db.Column(db.Integer, db.ForeignKey('auctions.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    has_paid_entry = db.Column(db.Boolean, default=False, nullable=False)  # Чи сплачено вхідну плату
    has_viewed_price = db.Column(db.Boolean, default=False, nullable=False)  # Чи переглянув поточну ціну

    # Встановлення зв'язків
    auction = db.relationship('Auction', back_populates='participants')
    user = db.relationship('User', back_populates='auction_participations')

    def __init__(self, auction_id, user_id):
        self.auction_id = auction_id
        self.user_id = user_id

    def mark_paid_entry(self):
        """
        Позначає, що користувач сплатив вхідну плату.
        """
        self.has_paid_entry = True

    def mark_viewed_price(self):
        self.has_viewed_price = True
        db.session.commit()  # Збереження змін

