# services/payment_service.py
from app import db
from app.models.payment import Payment
from app.models.user import User
from app.models.auction_participant import AuctionParticipant

class PaymentService:

    @staticmethod
    def add_balance(user_email, amount):
        """
        Додає кошти до балансу користувача.
        """
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return {"message": "Користувача не знайдено"}, 404

        if amount <= 0:
            return {"message": "Сума поповнення має бути більше нуля"}, 400

        user.balance += amount
        db.session.commit()
        return {"message": f"Баланс успішно поповнено. Новий баланс: {user.balance}"}, 200

    @staticmethod
    def process_entry_payment(user_email, auction_id, amount):
        """
        Обробляє платіж за участь в аукціоні.
        """
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return {"message": "Користувача не знайдено"}, 404

        # Перевірка, чи користувач вже сплатив за участь
        participation = AuctionParticipant.query.filter_by(user_id=user.id, auction_id=auction_id).first()
        if participation and participation.has_paid_entry:
            return {"message": "Ви вже оплатили участь у цьому аукціоні"}, 400

        if user.balance < amount:
            return {"message": "Недостатньо коштів на балансі"}, 400

        # Списання коштів з балансу користувача
        user.balance -= amount

        # Створення запису платежу
        new_payment = Payment(user_id=user.id, auction_id=auction_id, amount=amount, purpose='entry_fee', recipient='seller')
        db.session.add(new_payment)

        # Оновлення участі користувача
        if not participation:
            participation = AuctionParticipant(auction_id=auction_id, user_id=user.id)
            db.session.add(participation)
        participation.mark_paid_entry()

        db.session.commit()

        # Обробка платежу
        new_payment.process_payment()

        return {"message": f"Платіж на суму {amount} успішно проведено. Залишок балансу: {user.balance}"}, 200

    @staticmethod
    def process_view_payment(user_email, auction_id, amount):
        """
        Обробляє платіж за перегляд поточної ціни аукціону.
        """
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return {"message": "Користувача не знайдено"}, 404

        # Перевірка наявності коштів
        if user.balance < amount:
            return {"message": "Недостатньо коштів на балансі для перегляду"}, 400

        # Перевірка, чи користувач вже переглядав ціну
        participation = AuctionParticipant.query.filter_by(user_id=user.id, auction_id=auction_id).first()
        if participation and participation.has_viewed_price:
            return {"message": "Ви вже переглянули поточну ціну"}, 400

        # Списання коштів з балансу користувача
        user.balance -= amount

        # Створення запису платежу
        new_payment = Payment(user_id=user.id, auction_id=auction_id, amount=amount, purpose='view_fee', recipient='auction')
        db.session.add(new_payment)

        # Оновлення участі
        if not participation:
            participation = AuctionParticipant(auction_id=auction_id, user_id=user.id)
            db.session.add(participation)
        participation.mark_viewed_price()

        db.session.commit()

        # Обробка платежу
        new_payment.process_payment()

        return {"message": f"Платіж за перегляд на суму {amount} успішно проведено. Залишок балансу: {user.balance}"}, 200
