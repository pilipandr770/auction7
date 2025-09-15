#!/usr/bin/env python3
"""
Database initialization script for Auction7
"""

from auction7.app import create_app, db
from auction7.app.models.user import User
from auction7.app.models.auction import Auction
from auction7.app.models.payment import Payment
from auction7.app.models.auction_participant import AuctionParticipant

def init_database():
    """Initialize the database with tables and some sample data"""
    app = create_app()
    
    with app.app_context():
        # Create all tables
        print("Creating database tables...")
        db.create_all()
        
        # Check if admin user already exists
        admin_user = User.query.filter_by(email='admin@auction7.com').first()
        if not admin_user:
            # Create admin user
            admin_user = User(
                username='admin',
                email='admin@auction7.com',
                password='admin123',
                user_type='admin',
                is_admin=True
            )
            admin_user.balance = 1000.0
            db.session.add(admin_user)
            print("Created admin user: admin@auction7.com / admin123")
        
        # Create sample buyer user
        buyer_user = User.query.filter_by(email='buyer@test.com').first()
        if not buyer_user:
            buyer_user = User(
                username='buyer1',
                email='buyer@test.com',
                password='buyer123',
                user_type='buyer'
            )
            buyer_user.balance = 500.0
            db.session.add(buyer_user)
            print("Created buyer user: buyer@test.com / buyer123")
        
        # Create sample seller user
        seller_user = User.query.filter_by(email='seller@test.com').first()
        if not seller_user:
            seller_user = User(
                username='seller1',
                email='seller@test.com',
                password='seller123',
                user_type='seller'
            )
            seller_user.balance = 100.0
            db.session.add(seller_user)
            db.session.commit()  # Commit to get IDs
            print("Created seller user: seller@test.com / seller123")
            
            # Create sample auction
            sample_auction = Auction.query.filter_by(title='Sample Vintage Watch').first()
            if not sample_auction:
                sample_auction = Auction(
                    title='Sample Vintage Watch',
                    description='Beautiful vintage watch from the 1960s in excellent condition. Perfect for collectors.',
                    starting_price=100.0,
                    seller_id=seller_user.id,
                    photos=['images/uploads/aa748f62-232e-4283-ba81-5b96ca03a68a.jpg']
                )
                db.session.add(sample_auction)
                print("Created sample auction: Sample Vintage Watch")
        
        db.session.commit()
        print("Database initialized successfully!")

if __name__ == '__main__':
    init_database()