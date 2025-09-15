# Payment Routes with Stripe Integration
from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from auction7.app.services.stripe_payment_service import EnhancedPaymentService, StripePaymentService
from auction7.app.models.payment import Payment
import stripe
import os

payment_bp = Blueprint('payment', __name__)

@payment_bp.route('/topup', methods=['GET', 'POST'])
@login_required
def balance_topup():
    """Сторінка поповнення балансу"""
    if request.method == 'POST':
        try:
            amount = float(request.form.get('amount', 0))
            if amount <= 0:
                flash('Сума повинна бути більше нуля', 'error')
                return render_template('payment/balance_topup.html')
            
            if amount > 1000:  # Максимальна сума поповнення
                flash('Максимальна сума поповнення: $1000', 'error')
                return render_template('payment/balance_topup.html')
            
            # Створюємо Stripe Checkout сесію
            result, status = EnhancedPaymentService.add_balance_via_stripe(
                current_user.email, amount
            )
            
            if status == 200:
                return redirect(result['checkout_url'])
            else:
                flash(result['message'], 'error')
                
        except ValueError:
            flash('Невірний формат суми', 'error')
        except Exception as e:
            flash(f'Помилка: {str(e)}', 'error')
    
    # Отримуємо історію платежів користувача
    recent_payments = Payment.query.filter_by(
        user_id=current_user.id, 
        purpose='balance_topup'
    ).order_by(Payment.created_at.desc()).limit(5).all()
    
    return render_template('payment/balance_topup.html', 
                         current_balance=current_user.balance,
                         recent_payments=recent_payments)

@payment_bp.route('/success')
@login_required
def payment_success():
    """Сторінка успішної оплати"""
    session_id = request.args.get('session_id')
    
    if session_id:
        try:
            stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
            session = stripe.checkout.Session.retrieve(session_id)
            
            # Знаходимо платіж в базі даних
            payment = Payment.query.filter_by(
                stripe_session_id=session_id,
                user_id=current_user.id
            ).first()
            
            if payment:
                flash(f'Баланс успішно поповнено на {payment.get_formatted_amount()}!', 'success')
            else:
                flash('Платіж успішно завершено!', 'success')
                
        except Exception as e:
            current_app.logger.error(f"Error retrieving session: {str(e)}")
            flash('Платіж завершено, але виникла помилка при обробці', 'warning')
    
    return redirect(url_for('user.profile'))

@payment_bp.route('/cancel')
@login_required
def payment_cancel():
    """Сторінка скасування оплати"""
    flash('Оплату було скасовано', 'info')
    return redirect(url_for('payment.balance_topup'))

@payment_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Webhook для обробки подій від Stripe"""
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        stripe_service = StripePaymentService()
        stripe_service.handle_webhook(payload, sig_header)
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        current_app.logger.error(f"Webhook error: {str(e)}")
        return jsonify({'error': str(e)}), 400

@payment_bp.route('/history')
@login_required
def payment_history():
    """Історія платежів користувача"""
    page = request.args.get('page', 1, type=int)
    payments = Payment.query.filter_by(user_id=current_user.id)\
        .order_by(Payment.created_at.desc())\
        .paginate(page=page, per_page=20, error_out=False)
    
    return render_template('payment/history.html', payments=payments)

@payment_bp.route('/receipt/<int:payment_id>')
@login_required
def payment_receipt(payment_id):
    """Квитанція про платіж"""
    payment = Payment.query.filter_by(id=payment_id, user_id=current_user.id).first_or_404()
    
    # Отримуємо додаткову інформацію від Stripe, якщо є
    stripe_details = None
    if payment.stripe_charge_id:
        try:
            stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
            stripe_details = stripe.Charge.retrieve(payment.stripe_charge_id)
        except:
            pass
    
    return render_template('payment/receipt.html', 
                         payment=payment, 
                         stripe_details=stripe_details)

@payment_bp.route('/api/create-payment-intent', methods=['POST'])
@login_required
def create_payment_intent():
    """API endpoint для створення Payment Intent"""
    try:
        data = request.get_json()
        amount = float(data.get('amount', 0))
        purpose = data.get('purpose', 'balance_topup')
        
        if amount <= 0:
            return jsonify({'error': 'Невірна сума'}), 400
            
        stripe_service = StripePaymentService()
        amount_cents = int(amount * 100)
        
        intent = stripe_service.create_payment_intent(
            amount_cents=amount_cents,
            user_id=current_user.id,
            metadata={
                'purpose': purpose,
                'user_email': current_user.email
            }
        )
        
        return jsonify({
            'client_secret': intent['client_secret'],
            'publishable_key': stripe_service.publishable_key
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500