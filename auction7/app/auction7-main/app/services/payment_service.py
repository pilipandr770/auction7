# services/payment_service.py
from app import db
from app.models.payment import Payment
from app.models.user import User
from app.models.auction_participant import AuctionParticipant
from blockchain_payments.payment_token_discount import get_user_discount

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
        Обробляє платіж за участь в аукціоні з урахуванням знижки за токен.
        """
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return {"message": "Користувача не знайдено"}, 404

        # Застосування знижки за токен
        from app.services.payment_service import calculate_discounted_price
        discounted_amount = calculate_discounted_price(user.wallet_address, amount)

        # Перевірка, чи користувач вже сплатив за участь
        participation = AuctionParticipant.query.filter_by(user_id=user.id, auction_id=auction_id).first()
        if participation and participation.has_paid_entry:
            return {"message": "Ви вже оплатили участь у цьому аукціоні"}, 400

        if user.balance < discounted_amount:
            return {"message": "Недостатньо коштів на балансі"}, 400

        # Списання коштів з балансу користувача
        user.balance -= discounted_amount

        # Створення запису платежу
        new_payment = Payment(user_id=user.id, auction_id=auction_id, amount=discounted_amount, purpose='entry_fee', recipient='seller')
        db.session.add(new_payment)

        # Оновлення участі користувача
        if not participation:
            participation = AuctionParticipant(auction_id=auction_id, user_id=user.id)
            db.session.add(participation)
        participation.mark_paid_entry()

        db.session.commit()

        # Обробка платежу
        new_payment.process_payment()

        return {"message": f"Платіж на суму {discounted_amount} успішно проведено. Залишок балансу: {user.balance}"}, 200

    @staticmethod
    def process_view_payment(user_email, auction_id, amount):
        """
        Обробляє платіж за перегляд поточної ціни аукціону з урахуванням знижки за токен.
        """
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return {"message": "Користувача не знайдено"}, 404

        # Застосування знижки за токен
        from app.services.payment_service import calculate_discounted_price
        discounted_amount = calculate_discounted_price(user.wallet_address, amount)

        # Перевірка наявності коштів
        if user.balance < discounted_amount:
            return {"message": "Недостатньо коштів на балансі для перегляду"}, 400

        # Перевірка, чи користувач вже переглядав ціну
        participation = AuctionParticipant.query.filter_by(user_id=user.id, auction_id=auction_id).first()
        if participation and participation.has_viewed_price:
            return {"message": "Ви вже переглянули поточну ціну"}, 400

        # Списання коштів з балансу користувача
        user.balance -= discounted_amount

        # Створення запису платежу
        new_payment = Payment(user_id=user.id, auction_id=auction_id, amount=discounted_amount, purpose='view_fee', recipient='auction')
        db.session.add(new_payment)

        # Оновлення участі
        if not participation:
            participation = AuctionParticipant(auction_id=auction_id, user_id=user.id)
            db.session.add(participation)
        participation.mark_viewed_price()

        db.session.commit()

        # Обробка платежу
        new_payment.process_payment()

        return {"message": f"Платіж за перегляд на суму {discounted_amount} успішно проведено. Залишок балансу: {user.balance}"}, 200

def calculate_discounted_price(wallet_address, price):
    """
    Повертає ціну з урахуванням знижки для користувача за токен.
    """
    if wallet_address:
        discount = get_user_discount(wallet_address)
        if discount > 0:
            return price * (100 - discount) / 100
    return price
