# services/payment_service.py
from app import db
from app.models.payment import Payment
from app.models.user import User

class PaymentService:

    @staticmethod
    def add_balance(user_email, amount):
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return {"message": "Користувача не знайдено"}, 404

        user.balance += amount
        db.session.commit()
        return {"message": f"Баланс успішно поповнено. Новий баланс: {user.balance}"}, 200

    @staticmethod
    def process_entry_payment(user_email, auction_id, amount):
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return {"message": "Користувача не знайдено"}, 404

        if user.balance < amount:
            return {"message": "Недостатньо коштів на балансі"}, 400

        # Знімаємо кошти з балансу користувача
        user.balance -= amount

        # Створюємо платіж
        new_payment = Payment(user_id=user.id, auction_id=auction_id, amount=amount, purpose='entry_fee', recipient='seller')
        db.session.add(new_payment)
        db.session.commit()

        # Обробляємо платіж
        new_payment.process_payment()

        return {"message": f"Платіж на суму {amount} успішно проведено. Залишок балансу: {user.balance}"}, 200
