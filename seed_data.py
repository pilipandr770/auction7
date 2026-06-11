"""Створення таблиць та тестових даних для локальної розробки."""
from app import create_app, db
from app.models.user import User
from app.models.auction import Auction

app = create_app()

with app.app_context():
    db.create_all()

    if not User.query.filter_by(email='seller@dropbid.test').first():
        seller = User(username='TechStore', email='seller@dropbid.test', password='test1234', user_type='seller')
        db.session.add(seller)

        buyer = User(username='Käufer', email='buyer@dropbid.test', password='test1234', user_type='buyer')
        buyer.balance = 5000.0
        db.session.add(buyer)

        admin = User(username='Admin', email='admin@dropbid.test', password='test1234', user_type='admin', is_admin=True)
        db.session.add(admin)
        db.session.commit()

        lots = [
            ('Apple iPhone 15 Pro 256GB', 'Neu, originalverpackt. 12 Monate Garantie. Farbe Natural Titanium.', 1000),
            ('Sony PlayStation 5 + 2 Controller', 'Disc Edition, Set mit zwei DualSense-Controllern.', 600),
            ('MacBook Air M2 512GB', 'Space Grey, 16GB RAM. Neuwertiger Zustand.', 1400),
            ('Dyson V15 Detect', 'Kabelloser Staubsauger mit Laser-Staubdetektor.', 550),
            ('Canon EOS R6 Mark II', 'Spiegellose Kamera, nur Body. 2.000 Auslösungen.', 2200),
            ('Apple Watch Ultra 2', 'Titan, 49mm. Mit Trail Loop Armband.', 900),
        ]
        for title, desc, price in lots:
            db.session.add(Auction(title=title, description=desc, starting_price=price, seller_id=seller.id))
        db.session.commit()
        print('Seeded users + auctions')
    else:
        print('Data already exists')

    print('Users:', User.query.count(), 'Auctions:', Auction.query.count())
