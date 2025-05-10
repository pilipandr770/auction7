from flask import Blueprint, render_template, session, redirect, request
from flask_login import current_user
from blockchain_payments.payment_token_discount import get_user_discount
from app.models.auction import Auction

main_bp = Blueprint('main', __name__)

# --- Головна сторінка ---
@main_bp.route('/')
def index():
    lang = session.get('lang', 'ua')
    if lang == 'en':
        return redirect('/en')
    elif lang == 'de':
        return redirect('/de')
    auctions = Auction.query.filter_by(is_active=True).all()
    discount = None
    if current_user.is_authenticated and current_user.wallet_address:
        try:
            discount = get_user_discount(current_user.wallet_address)
        except Exception:
            discount = None
    return render_template('index.html', auctions=auctions, user_discount=discount, lang=lang)

@main_bp.route('/en')
def index_en():
    lang = session.get('lang', 'en')
    if lang == 'ua':
        return redirect('/')
    elif lang == 'de':
        return redirect('/de')
    auctions = Auction.query.filter_by(is_active=True).all()
    discount = None
    if current_user.is_authenticated and current_user.wallet_address:
        try:
            discount = get_user_discount(current_user.wallet_address)
        except Exception:
            discount = None
    return render_template('index_en.html', auctions=auctions, user_discount=discount, lang=lang)

@main_bp.route('/de')
def index_de():
    lang = session.get('lang', 'de')
    if lang == 'ua':
        return redirect('/')
    elif lang == 'en':
        return redirect('/en')
    auctions = Auction.query.filter_by(is_active=True).all()
    discount = None
    if current_user.is_authenticated and current_user.wallet_address:
        try:
            discount = get_user_discount(current_user.wallet_address)
        except Exception:
            discount = None
    return render_template('index_de.html', auctions=auctions, user_discount=discount, lang=lang)

# --- Privacy ---
@main_bp.route('/privacy')
def privacy():
    lang = session.get('lang', 'ua')
    if lang == 'en':
        return redirect('/en/privacy')
    elif lang == 'de':
        return redirect('/de/privacy')
    return render_template('privacy.html', lang=lang)

@main_bp.route('/en/privacy')
def privacy_en():
    lang = session.get('lang', 'en')
    if lang == 'ua':
        return redirect('/privacy')
    elif lang == 'de':
        return redirect('/de/privacy')
    return render_template('privacy_en.html', lang=lang)

@main_bp.route('/de/privacy')
def privacy_de():
    lang = session.get('lang', 'de')
    if lang == 'ua':
        return redirect('/privacy')
    elif lang == 'en':
        return redirect('/en/privacy')
    return render_template('privacy_de.html', lang=lang)

# --- Impressum ---
@main_bp.route('/impressum')
def impressum():
    lang = session.get('lang', 'ua')
    if lang == 'en':
        return redirect('/en/impressum')
    elif lang == 'de':
        return redirect('/de/impressum')
    return render_template('impressum.html', lang=lang)

@main_bp.route('/en/impressum')
def impressum_en():
    lang = session.get('lang', 'en')
    if lang == 'ua':
        return redirect('/impressum')
    elif lang == 'de':
        return redirect('/de/impressum')
    return render_template('impressum_en.html', lang=lang)

@main_bp.route('/de/impressum')
def impressum_de():
    lang = session.get('lang', 'de')
    if lang == 'ua':
        return redirect('/impressum')
    elif lang == 'en':
        return redirect('/en/impressum')
    return render_template('impressum_de.html', lang=lang)

# --- Contacts ---
@main_bp.route('/contacts')
def contacts():
    lang = session.get('lang', 'ua')
    if lang == 'en':
        return redirect('/en/contacts')
    elif lang == 'de':
        return redirect('/de/contacts')
    return render_template('contacts.html', lang=lang)

@main_bp.route('/en/contacts')
def contacts_en():
    lang = session.get('lang', 'en')
    if lang == 'ua':
        return redirect('/contacts')
    elif lang == 'de':
        return redirect('/de/contacts')
    return render_template('contacts_en.html', lang=lang)

@main_bp.route('/de/contacts')
def contacts_de():
    lang = session.get('lang', 'de')
    if lang == 'ua':
        return redirect('/contacts')
    elif lang == 'en':
        return redirect('/en/contacts')
    return render_template('contacts_de.html', lang=lang)

# --- Language Switcher ---
@main_bp.route('/set_language/<lang>')
def set_language(lang):
    if lang in ['ua', 'en', 'de']:
        session['lang'] = lang
    # Повертаємо користувача на попередню сторінку, якщо можливо
    ref = request.referrer
    # Визначаємо, на яку сторінку редіректити
    if ref and not ref.endswith('/set_language/' + lang):
        # Якщо ref містить /en/ або /de/ або /ua/ - замінити на нову мову
        import re
        new_ref = re.sub(r'/(en|de|ua)(/|$)', f'/{lang}\2', ref)
        # Якщо не було мовного префіксу, додати його (крім ua)
        if lang != 'ua' and not re.search(r'/(en|de)(/|$)', ref):
            if ref.endswith('/'):
                new_ref = f'/{lang}' + ref
            else:
                new_ref = f'/{lang}' + ref if ref.startswith('/') else f'/{lang}/{ref}'
        if lang == 'ua':
            # Повернути на українську без префікса
            new_ref = re.sub(r'/en/|/de/', '/', ref)
        return redirect(new_ref)
    # Якщо немає referrer, редірект на головну відповідної мови
    if lang == 'en':
        return redirect('/en')
    elif lang == 'de':
        return redirect('/de')
    return redirect('/')

# --- Flutter routes (аналогічно) ---
@main_bp.route('/privacy_flutter')
def privacy_flutter():
    lang = session.get('lang', 'ua')
    if lang == 'en':
        return redirect('/en/privacy')
    elif lang == 'de':
        return redirect('/de/privacy')
    return redirect('/privacy')

@main_bp.route('/contacts_flutter')
def contacts_flutter():
    lang = session.get('lang', 'ua')
    if lang == 'en':
        return redirect('/en/contacts')
    elif lang == 'de':
        return redirect('/de/contacts')
    return redirect('/contacts')

@main_bp.route('/impressum_flutter')
def impressum_flutter():
    lang = session.get('lang', 'ua')
    if lang == 'en':
        return redirect('/en/impressum')
    elif lang == 'de':
        return redirect('/de/impressum')
    return redirect('/impressum')
