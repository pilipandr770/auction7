"""Маршрути платежів: Connect онбординг, сервіс-кредити, збереження картки, webhook."""
from flask import (Blueprint, redirect, url_for, flash, request, jsonify,
                   render_template, current_app)
from flask_login import login_required, current_user

from app import db, limiter, csrf
from app.models.user import User
from app.models.transaction import Transaction
from app.payments import stripe_service as ss

payments_bp = Blueprint('payments', __name__, url_prefix='/payments')


def _base_url():
    return current_app.config['APP_BASE_URL'].rstrip('/')


# ── Продавець: Connect Express онбординг ──────────────────────────────────────

@payments_bp.route('/connect/onboard', methods=['POST', 'GET'])
@login_required
def connect_onboard():
    if current_user.user_type != 'seller':
        flash("Nur Verkäufer können Auszahlungen aktivieren.", "error")
        return redirect(url_for('main.index'))
    if not ss.is_configured():
        flash("Zahlungen sind noch nicht konfiguriert (keine Stripe-Schlüssel).", "error")
        return redirect(url_for('user.seller_dashboard', email=current_user.email))
    try:
        account_id = ss.ensure_connect_account(current_user)
        db.session.commit()
        link = ss.create_account_link(
            account_id,
            refresh_url=f"{_base_url()}/payments/connect/onboard",
            return_url=f"{_base_url()}/payments/connect/return",
        )
        return redirect(link.url)
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Connect onboard error: {e}")
        flash("Onboarding konnte nicht gestartet werden. Bitte später erneut versuchen.", "error")
        return redirect(url_for('user.seller_dashboard', email=current_user.email))


@payments_bp.route('/connect/return')
@login_required
def connect_return():
    """Повернення після онбордингу — перевіряємо чи виплати активовано."""
    try:
        if current_user.stripe_account_id:
            enabled = ss.account_payouts_enabled(current_user.stripe_account_id)
            current_user.stripe_payouts_enabled = enabled
            db.session.commit()
            flash("Auszahlungen aktiviert! Sie können nun Erlöse erhalten." if enabled
                  else "Onboarding noch nicht abgeschlossen. Bitte schließen Sie alle Schritte in Stripe ab.",
                  "success" if enabled else "info")
    except Exception as e:
        current_app.logger.error(f"Connect return error: {e}")
    return redirect(url_for('user.seller_dashboard', email=current_user.email))


# ── Покупець: сервіс-кредити ─────────────────────────────────────────────────

@payments_bp.route('/credits/buy', methods=['POST'])
@login_required
@limiter.limit("5 per minute")
def buy_credits():
    if not ss.is_configured():
        flash("Zahlungen sind noch nicht konfiguriert.", "error")
        return redirect(url_for('user.buyer_dashboard', email=current_user.email))
    try:
        quantity = int(request.form.get('quantity', 50))
    except ValueError:
        quantity = 50
    quantity = max(1, min(quantity, 1000))
    unit_price = current_app.config['CREDIT_PRICE_EUR']
    try:
        session = ss.create_credits_checkout(
            current_user, quantity, unit_price,
            success_url=f"{_base_url()}/payments/credits/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{_base_url()}/user/buyer/{current_user.email}",
        )
        db.session.commit()
        # Реєструємо намір (нарахування відбудеться у webhook після оплати)
        db.session.add(Transaction(type='topup_credits', user_id=current_user.id,
                                   amount_eur=quantity * unit_price, credits_delta=quantity,
                                   stripe_id=session.id, status='pending'))
        db.session.commit()
        return redirect(session.url)
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Credits checkout error: {e}")
        flash("Zahlung konnte nicht erstellt werden.", "error")
        return redirect(url_for('user.buyer_dashboard', email=current_user.email))


@payments_bp.route('/credits/success')
@login_required
def credits_success():
    # Fallback без webhook (localhost): перевіряємо сесію і зараховуємо, якщо оплачено.
    session_id = request.args.get('session_id')
    if session_id and ss.is_configured():
        try:
            import stripe
            stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
            sess = stripe.checkout.Session.retrieve(session_id)
            if sess.payment_status == 'paid':
                _credit_session(session_id)
        except Exception as e:
            current_app.logger.error(f"credits_success verify error: {e}")
    flash("Vielen Dank! Kredite wurden gutgeschrieben.", "success")
    return redirect(url_for('user.buyer_dashboard', email=current_user.email))


def _credit_session(session_id):
    """Ідемпотентне зарахування кредитів за оплаченою Checkout-сесією."""
    txn = Transaction.query.filter_by(stripe_id=session_id).first()
    if not txn or txn.status == 'succeeded':
        return
    user = db.session.get(User, txn.user_id)
    if user:
        user.service_credits = (user.service_credits or 0) + txn.credits_delta
        txn.status = 'succeeded'
        db.session.commit()


# ── Покупець: збереження картки (SetupIntent) ────────────────────────────────

@payments_bp.route('/card/setup', methods=['GET'])
@login_required
def card_setup():
    if not ss.is_configured():
        flash("Zahlungen sind noch nicht konfiguriert.", "error")
        return redirect(url_for('user.buyer_dashboard', email=current_user.email))
    intent = ss.create_setup_intent(current_user)
    db.session.commit()
    return render_template('payments/card_setup.html',
                           client_secret=intent.client_secret,
                           publishable_key=current_app.config['STRIPE_PUBLISHABLE_KEY'])


@payments_bp.route('/card/saved', methods=['POST'])
@login_required
def card_saved():
    """Викликається фронтом після успішного підтвердження SetupIntent."""
    pm = request.json.get('payment_method') if request.is_json else request.form.get('payment_method')
    if pm:
        current_user.default_payment_method = pm
        db.session.commit()
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "no payment_method"}), 400


# ── Webhook ───────────────────────────────────────────────────────────────────

@payments_bp.route('/webhook', methods=['POST'])
@csrf.exempt  # Stripe подписывает запрос своим HMAC — CSRF-токен не нужен
def webhook():
    payload = request.get_data()
    sig = request.headers.get('Stripe-Signature', '')
    try:
        event = ss.construct_event(payload, sig)
    except Exception as e:
        current_app.logger.error(f"Webhook signature error: {e}")
        return "bad signature", 400

    etype = event['type']
    obj = event['data']['object']

    if etype == 'checkout.session.completed':
        _handle_credits_paid(obj)
    elif etype == 'account.updated':
        _handle_account_updated(obj)

    return jsonify({"received": True})


def _handle_credits_paid(session_obj):
    """Зараховує кредити після успішної оплати Checkout (ідемпотентно)."""
    _credit_session(session_obj['id'])


def _handle_account_updated(account_obj):
    user = User.query.filter_by(stripe_account_id=account_obj['id']).first()
    if user:
        user.stripe_payouts_enabled = bool(account_obj.get('payouts_enabled'))
        db.session.commit()
