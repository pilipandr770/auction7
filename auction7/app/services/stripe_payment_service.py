# Enhanced Payment Service with Stripe Integration
import stripe
import os
from flask import current_app, request, url_for
from auction7.app import db
from auction7.app.models.payment import Payment
from auction7.app.models.user import User
from auction7.app.models.auction_participant import AuctionParticipant

try:
    from blockchain_payments.payment_token_discount import get_user_discount
except ImportError:
    # Fallback function if blockchain module is not available
    def get_user_discount(wallet_address):
        return 0

class StripePaymentService:
    
    def __init__(self):
        stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
        self.publishable_key = os.getenv('STRIPE_PUBLISHABLE_KEY')
    
    def create_payment_intent(self, amount_cents, currency='usd', user_id=None, metadata=None):
        """
        Створює Payment Intent для Stripe платежу
        :param amount_cents: Сума в центах (копійках)
        :param currency: Валюта платежу
        :param user_id: ID користувача
        :param metadata: Додаткові дані для платежу
        :return: Payment Intent об'єкт
        """
        try:
            intent_metadata = {
                'user_id': str(user_id) if user_id else None,
            }
            if metadata:
                intent_metadata.update(metadata)
                
            payment_intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=currency,
                metadata=intent_metadata,
                automatic_payment_methods={'enabled': True}
            )
            return payment_intent
        except stripe.error.StripeError as e:
            current_app.logger.error(f"Stripe error creating payment intent: {str(e)}")
            raise Exception(f"Помилка створення платежу: {str(e)}")
    
    def create_checkout_session(self, amount_cents, success_url, cancel_url, 
                               user_email=None, user_id=None, purpose='balance_topup'):
        """
        Створює Checkout Session для платежу через Stripe Checkout
        """
        try:
            session_data = {
                'payment_method_types': ['card'],
                'line_items': [{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': 'Поповнення балансу аукціонного аккаунта',
                            'description': f'Поповнення балансу на ${amount_cents/100:.2f}',
                        },
                        'unit_amount': amount_cents,
                    },
                    'quantity': 1,
                }],
                'mode': 'payment',
                'success_url': success_url,
                'cancel_url': cancel_url,
                'metadata': {
                    'user_id': str(user_id) if user_id else '',
                    'purpose': purpose,
                    'amount_cents': str(amount_cents),
                }
            }
            
            if user_email:
                session_data['customer_email'] = user_email
                
            session = stripe.checkout.Session.create(**session_data)
            return session
        except stripe.error.StripeError as e:
            current_app.logger.error(f"Stripe error creating checkout session: {str(e)}")
            raise Exception(f"Помилка створення платіжної сесії: {str(e)}")
    
    def handle_webhook(self, payload, sig_header):
        """
        Обробляє webhook від Stripe для підтвердження платежів
        """
        endpoint_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
        
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        except ValueError:
            current_app.logger.error("Invalid payload in Stripe webhook")
            raise Exception("Невірні дані webhook")
        except stripe.error.SignatureVerificationError:
            current_app.logger.error("Invalid signature in Stripe webhook")
            raise Exception("Невірний підпис webhook")

        # Обробка різних типів подій
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            self._handle_successful_payment(session)
        elif event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            self._handle_payment_intent_succeeded(payment_intent)
        elif event['type'] == 'payment_intent.payment_failed':
            payment_intent = event['data']['object']
            self._handle_payment_failed(payment_intent)
        
        return True
    
    def _handle_successful_payment(self, session):
        """
        Обробляє успішний платіж через Checkout
        """
        metadata = session.get('metadata', {})
        user_id = metadata.get('user_id')
        purpose = metadata.get('purpose', 'balance_topup')
        amount_cents = int(metadata.get('amount_cents', 0))
        
        if user_id and amount_cents > 0:
            user = User.query.get(user_id)
            if user:
                amount_usd = amount_cents / 100.0
                
                # Додаємо кошти до балансу користувача
                user.add_balance(amount_usd)
                
                # Створюємо запис платежу
                payment = Payment(
                    user_id=user.id,
                    amount=amount_usd,
                    purpose=purpose,
                    stripe_session_id=session['id'],
                    status='completed'
                )
                db.session.add(payment)
                db.session.commit()
                
                current_app.logger.info(f"Balance topup successful for user {user_id}: ${amount_usd}")
    
    def _handle_payment_intent_succeeded(self, payment_intent):
        """
        Обробляє успішний Payment Intent
        """
        metadata = payment_intent.get('metadata', {})
        user_id = metadata.get('user_id')
        
        if user_id:
            # Знаходимо платіж в базі даних і оновлюємо статус
            payment = Payment.query.filter_by(
                user_id=user_id,
                stripe_payment_intent_id=payment_intent['id']
            ).first()
            
            if payment:
                payment.status = 'completed'
                payment.stripe_charge_id = payment_intent.get('charges', {}).get('data', [{}])[0].get('id')
                db.session.commit()
    
    def _handle_payment_failed(self, payment_intent):
        """
        Обробляє невдалий Payment Intent
        """
        metadata = payment_intent.get('metadata', {})
        user_id = metadata.get('user_id')
        
        if user_id:
            payment = Payment.query.filter_by(
                user_id=user_id,
                stripe_payment_intent_id=payment_intent['id']
            ).first()
            
            if payment:
                payment.status = 'failed'
                payment.failure_reason = payment_intent.get('last_payment_error', {}).get('message', 'Unknown error')
                db.session.commit()


class EnhancedPaymentService(StripePaymentService):
    """
    Розширений сервіс платежів, який комбінує Stripe з існуючим функціоналом
    """
    
    @staticmethod
    def add_balance_via_stripe(user_email, amount_usd):
        """
        Створює Stripe Checkout сесію для поповнення балансу
        """
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return {"message": "Користувача не знайдено"}, 404

        if amount_usd <= 0:
            return {"message": "Сума поповнення має бути більше нуля"}, 400

        try:
            stripe_service = StripePaymentService()
            amount_cents = int(amount_usd * 100)
            
            success_url = url_for('user.payment_success', _external=True)
            cancel_url = url_for('user.payment_cancel', _external=True)
            
            session = stripe_service.create_checkout_session(
                amount_cents=amount_cents,
                success_url=success_url,
                cancel_url=cancel_url,
                user_email=user.email,
                user_id=user.id
            )
            
            return {
                "message": "Платіжна сесія створена", 
                "checkout_url": session.url,
                "session_id": session.id
            }, 200
            
        except Exception as e:
            return {"message": f"Помилка створення платежу: {str(e)}"}, 500
    
    @staticmethod
    def process_entry_payment(user_email, auction_id, amount):
        """
        Обробляє платіж за участь в аукціоні з урахуванням знижки за токен
        """
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return {"message": "Користувача не знайдено"}, 404

        # Застосування знижки за токен
        discounted_amount = calculate_discounted_price(user.wallet_address, amount)

        # Перевірка, чи користувач вже сплатив за участь
        participation = AuctionParticipant.query.filter_by(user_id=user.id, auction_id=auction_id).first()
        if participation and participation.has_paid_entry:
            return {"message": "Ви вже оплатили участь у цьому аукціоні"}, 400

        if user.balance < discounted_amount:
            # Пропонуємо поповнити баланс через Stripe
            shortfall = discounted_amount - user.balance
            return {
                "message": f"Недостатньо коштів на балансі. Потрібно ще ${shortfall:.2f}",
                "balance": user.balance,
                "required": discounted_amount,
                "shortfall": shortfall,
                "suggest_topup": True
            }, 400

        # Списання коштів з балансу користувача
        user.balance -= discounted_amount

        # Створення запису платежу
        new_payment = Payment(
            user_id=user.id, 
            auction_id=auction_id, 
            amount=discounted_amount, 
            purpose='entry_fee', 
            recipient='seller',
            status='completed'
        )
        db.session.add(new_payment)

        # Оновлення участі користувача
        if not participation:
            participation = AuctionParticipant(auction_id=auction_id, user_id=user.id)
            db.session.add(participation)
        participation.mark_paid_entry()

        db.session.commit()

        return {"message": f"Платіж на суму ${discounted_amount:.2f} успішно проведено. Залишок балансу: ${user.balance:.2f}"}, 200

    @staticmethod
    def process_view_payment(user_email, auction_id, amount):
        """
        Обробляє платіж за перегляд поточної ціни аукціону з урахуванням знижки за токен
        """
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return {"message": "Користувача не знайдено"}, 404

        # Застосування знижки за токен
        discounted_amount = calculate_discounted_price(user.wallet_address, amount)

        # Перевірка наявності коштів
        if user.balance < discounted_amount:
            shortfall = discounted_amount - user.balance
            return {
                "message": f"Недостатньо коштів на балансі для перегляду. Потрібно ще ${shortfall:.2f}",
                "balance": user.balance,
                "required": discounted_amount,
                "shortfall": shortfall,
                "suggest_topup": True
            }, 400

        # Перевірка, чи користувач вже переглядав ціну
        participation = AuctionParticipant.query.filter_by(user_id=user.id, auction_id=auction_id).first()
        if participation and participation.has_viewed_price:
            return {"message": "Ви вже переглянули поточну ціну"}, 400

        # Списання коштів з балансу користувача
        user.balance -= discounted_amount

        # Створення запису платежу
        new_payment = Payment(
            user_id=user.id, 
            auction_id=auction_id, 
            amount=discounted_amount, 
            purpose='view_fee', 
            recipient='auction',
            status='completed'
        )
        db.session.add(new_payment)

        # Оновлення участі
        if not participation:
            participation = AuctionParticipant(auction_id=auction_id, user_id=user.id)
            db.session.add(participation)
        participation.mark_viewed_price()

        db.session.commit()

        return {"message": f"Платіж за перегляд на суму ${discounted_amount:.2f} успішно проведено. Залишок балансу: ${user.balance:.2f}"}, 200


def calculate_discounted_price(wallet_address, price):
    """
    Повертає ціну з урахуванням знижки для користувача за токен
    """
    if wallet_address:
        try:
            discount = get_user_discount(wallet_address)
            if discount > 0:
                return price * (100 - discount) / 100
        except:
            # Якщо помилка з blockchain, повертаємо звичайну ціну
            pass
    return price