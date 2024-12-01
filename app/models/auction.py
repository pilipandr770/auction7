# models/auction.py

class Auction:
    def __init__(self, title, description, starting_price, seller_id):
        self.title = title
        self.description = description
        self.starting_price = starting_price
        self.current_price = starting_price
        self.seller_id = seller_id
        self.total_participants = 0
        self.is_active = True
        self.winner_id = None

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
        self.winner_id = winner_id if winner_id else None
