"""Централізована робота зі Stripe (Connect Express, EUR).

Гроші продавця (входи + закриття) тримає Stripe (ескроу через separate charges
& transfers). Дохід платформи — продаж сервіс-кредитів (перегляди), не e-money.
"""
import stripe
from flask import current_app


def _init():
    """Ініціалізує Stripe API ключем з конфігу. Викликати перед кожною операцією."""
    key = current_app.config.get('STRIPE_SECRET_KEY', '')
    if not key:
        raise RuntimeError("STRIPE_SECRET_KEY ist nicht konfiguriert (.env)")
    stripe.api_key = key
    return stripe


def is_configured():
    return bool(current_app.config.get('STRIPE_SECRET_KEY'))


def eur_to_cents(amount_eur):
    return int(round(float(amount_eur) * 100))


# ── Покупець: Customer + збережена картка ─────────────────────────────────────

def ensure_customer(user):
    """Повертає stripe_customer_id, створює Customer за потреби."""
    s = _init()
    if user.stripe_customer_id:
        return user.stripe_customer_id
    customer = s.Customer.create(email=user.email, name=user.username,
                                 metadata={'user_id': user.id})
    user.stripe_customer_id = customer.id
    return customer.id


def create_setup_intent(user):
    """SetupIntent для збереження картки покупця (off-session списання згодом)."""
    s = _init()
    customer_id = ensure_customer(user)
    return s.SetupIntent.create(customer=customer_id, usage='off_session',
                                payment_method_types=['card'])


# ── Сервіс-кредити (дохід платформи) ─────────────────────────────────────────

def create_credits_checkout(user, quantity, unit_price_eur, success_url, cancel_url):
    """Stripe Checkout для покупки сервіс-кредитів пачкою."""
    s = _init()
    customer_id = ensure_customer(user)
    return s.checkout.Session.create(
        mode='payment',
        customer=customer_id,
        line_items=[{
            'price_data': {
                'currency': 'eur',
                'product_data': {'name': f'{quantity} DropBid Service-Kredite (Preis-Einsicht)'},
                'unit_amount': eur_to_cents(unit_price_eur),
            },
            'quantity': quantity,
        }],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={'user_id': user.id, 'credits': quantity, 'kind': 'credits_topup'},
    )


# ── Продавець: Connect Express ────────────────────────────────────────────────

def ensure_connect_account(user):
    """Повертає stripe_account_id продавця, створює Express account за потреби."""
    s = _init()
    if user.stripe_account_id:
        return user.stripe_account_id
    account = s.Account.create(
        type='express',
        email=user.email,
        capabilities={'transfers': {'requested': True}},
        business_type='individual',
        metadata={'user_id': user.id},
    )
    user.stripe_account_id = account.id
    return account.id


def create_account_link(account_id, refresh_url, return_url):
    """Посилання на онбординг Connect Express (KYC, банк продавця)."""
    s = _init()
    return s.AccountLink.create(
        account=account_id,
        refresh_url=refresh_url,
        return_url=return_url,
        type='account_onboarding',
    )


def account_payouts_enabled(account_id):
    s = _init()
    acct = s.Account.retrieve(account_id)
    return bool(acct.payouts_enabled)


# ── Off-session платежі (вхід / закриття → ескроу платформи) ─────────────────

def charge_off_session(user, amount_eur, auction_id, kind):
    """Списує суму зі збереженої картки покупця в ескроу (баланс платформи).
    transfer_group прив'язує платіж до аукціону для подальшого transfer продавцю.
    Повертає PaymentIntent. Кидає stripe.error.CardError при деклайні.
    """
    s = _init()
    return s.PaymentIntent.create(
        amount=eur_to_cents(amount_eur),
        currency='eur',
        customer=user.stripe_customer_id,
        payment_method=user.default_payment_method,
        off_session=True,
        confirm=True,
        transfer_group=f'auction_{auction_id}',
        metadata={'user_id': user.id, 'auction_id': auction_id, 'kind': kind},
    )


# ── Виплата продавцю з ескроу ─────────────────────────────────────────────────

def transfer_to_seller(seller_account_id, amount_eur, auction_id):
    """Переводить ескроу-кошти на connected account продавця (потім payout)."""
    s = _init()
    return s.Transfer.create(
        amount=eur_to_cents(amount_eur),
        currency='eur',
        destination=seller_account_id,
        transfer_group=f'auction_{auction_id}',
        metadata={'auction_id': auction_id},
    )


# ── Webhook ───────────────────────────────────────────────────────────────────

def construct_event(payload, sig_header):
    """Перевіряє підпис webhook і повертає подію."""
    s = _init()
    secret = current_app.config.get('STRIPE_WEBHOOK_SECRET', '')
    return s.Webhook.construct_event(payload, sig_header, secret)
