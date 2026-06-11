from flask import Blueprint, request, jsonify, redirect, url_for, flash, render_template, current_app
from flask_login import login_required, current_user, logout_user
import secrets
from app import db, limiter
from app.models.user import User
from app.models.auction import Auction
from app.models.auction_participant import AuctionParticipant
from app.models.transaction import Transaction
from app.payments import stripe_service as ss
from app.services import mail
from blockchain_payments.payment_matic import process_payment, send_to_escrow, send_to_admin, release_from_escrow
import stripe

user_bp = Blueprint('user', __name__)


def notify_auction_end(auction, winner):
    """E-Mails bei Auktionsende: Gewinner & Verkäufer (Kontaktaustausch) + übrige Teilnehmer."""
    try:
        seller = db.session.get(User, auction.seller_id)
        title = auction.title

        if winner and seller:
            mail.send_email(
                winner.email,
                f"Sie haben die Auktion gewonnen: {title}",
                f"Herzlichen Glückwunsch!\n\n"
                f"Sie haben die Auktion '{title}' gewonnen.\n\n"
                f"Verkäufer: {seller.username}\nE-Mail: {seller.email}\n\n"
                f"Bitte kontaktieren Sie den Verkäufer zur Übergabe bzw. zum Versand.\n"
                f"Ihre Zahlung liegt im Treuhand und wird erst nach Ihrer Empfangsbestätigung "
                f"an den Verkäufer ausgezahlt.\n\nIhr DropBid-Team"
            )
            mail.send_email(
                seller.email,
                f"Ihr Artikel wurde verkauft: {title}",
                f"Guten Tag {seller.username},\n\n"
                f"Ihr Artikel '{title}' wurde über DropBid verkauft.\n\n"
                f"Käufer: {winner.username}\nE-Mail: {winner.email}\n\n"
                f"Bitte vereinbaren Sie Übergabe/Versand. Die Auszahlung erfolgt automatisch, "
                f"sobald der Käufer den Erhalt bestätigt.\n\nIhr DropBid-Team"
            )

        parts = AuctionParticipant.query.filter_by(auction_id=auction.id).all()
        others = set()
        for p in parts:
            if winner and p.user_id == winner.id:
                continue
            u = db.session.get(User, p.user_id)
            if u and u.email:
                others.add(u.email)
        if others:
            mail.send_many(
                others,
                f"Auktion beendet: {title}",
                f"Die Auktion '{title}' ist beendet.\n\n"
                f"Leider haben Sie diesmal nicht gewonnen. Danke für Ihre Teilnahme!\n\n"
                f"Ihr DropBid-Team"
            )
    except Exception as e:
        print(f"notify_auction_end error: {e}")

@user_bp.route('/add_balance', methods=['POST'])
@login_required
def add_balance():
    # Баланс поповнюється тільки через Stripe (payments/credits/buy).
    # Прямий endpoint для довільного поповнення видалено з міркувань безпеки.
    return jsonify({"error": "Nicht verfügbar. Bitte Guthaben über die Zahlungsseite aufladen."}), 403

@user_bp.route('/buyer/<string:email>', methods=['GET', 'POST'])
@login_required
def buyer_dashboard(email):
    if current_user.email != email:
        flash("Nicht autorisierter Zugriff", 'error')
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash("Benutzer nicht gefunden", 'error')
        return redirect(url_for('auth.login'))

    # Активні аукціони
    auctions = Auction.query.filter_by(is_active=True).all()
    # Аукціони, які очікують підтвердження отримання (переможець — поточний користувач)
    pending_confirmations = Auction.query.filter_by(is_active=False, is_confirmed=False, winner_id=current_user.id).all()
    # Підтверджені виграші, які ще не оцінені → можна залишити відгук
    from app.models.review import Review
    confirmed_won = Auction.query.filter_by(is_active=False, is_confirmed=True, winner_id=current_user.id).all()
    reviewed_ids = {r.auction_id for r in Review.query.filter_by(reviewer_id=current_user.id).all()}
    reviewable = [a for a in confirmed_won if a.id not in reviewed_ids]

    if request.method == 'POST':
        auction_id = request.form.get('auction_id')
        auction = Auction.query.get(auction_id)

        if not auction:
            flash("Auktion nicht gefunden.", "error")
            return redirect(url_for('user.buyer_dashboard', email=current_user.email))

        try:
            view_price = 1.0  # Платний перегляд — щоразу, дохід платформи
            participant = AuctionParticipant.query.filter_by(auction_id=auction.id, user_id=current_user.id).first()

            if current_user.balance < view_price:
                flash("Nicht genügend Guthaben für die Preis-Einsicht.", "error")
                return redirect(url_for('user.buyer_dashboard', email=current_user.email))

            current_user.deduct_balance(view_price)

            # Дохід платформи (адміністратор), а не продавця
            admin = User.query.filter_by(is_admin=True).first()
            if admin:
                admin.add_balance(view_price)
                admin.platform_balance = (admin.platform_balance or 0) + view_price

            if not participant:
                participant = AuctionParticipant(auction_id=auction.id, user_id=current_user.id)
                db.session.add(participant)

            participant.has_viewed_price = True
            db.session.commit()

            flash(f"Preis-Einsicht erfolgreich! Aktueller Preis: {auction.current_price} €", "success")
        except Exception as e:
            db.session.rollback()
            print(f"Fehler bei der Preis-Einsicht: {e}")
            flash("Einsicht fehlgeschlagen. Bitte später erneut versuchen.", "error")

    return render_template('users/buyer_dashboard.html', user=user, auctions=auctions, pending_confirmations=pending_confirmations, reviewable=reviewable)

@user_bp.route('/seller/<string:email>', methods=['GET'])
@login_required
def seller_dashboard(email):
    if current_user.email != email:
        flash("Nicht autorisierter Zugriff", 'error')
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash("Benutzer nicht gefunden", 'error')
        return redirect(url_for('auth.login'))

    all_auctions = Auction.query.filter_by(seller_id=user.id).all()

    # Активні аукціони продавця — БЕЗ ціни та кількості учасників (таємниця навіть для продавця)
    active_auctions = [
        {'id': a.id, 'title': a.title, 'seller_confirmed': a.seller_confirmed}
        for a in all_auctions if a.is_active
    ]

    completed_auctions = [
        {
            'title': auction.title,
            'description': auction.description,
            'starting_price': auction.starting_price,
            'status': 'Beendet' if not auction.is_active else 'Aktiv',
            'total_earnings': round(auction.total_participants * auction.starting_price * 0.01 + auction.current_price, 2),
            'total_participants': auction.total_participants
        }
        for auction in all_auctions if not auction.is_active
    ]

    balance_from_completed = sum(
        auction['total_earnings'] for auction in completed_auctions
    )

    return render_template(
        'users/seller_dashboard.html',
        user=user,
        auctions=completed_auctions,
        active_auctions=active_auctions,
        balance_from_completed=balance_from_completed
    )

@user_bp.route('/participate/<int:auction_id>', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def participate_in_auction(auction_id):
    auction = Auction.query.get(auction_id)
    if not auction or not auction.is_active:
        return jsonify({"error": "Auktion nicht gefunden oder bereits beendet"}), 400

    # Серверне вікно заморозки: нові входи заблоковані на 5 сек
    if auction.is_frozen():
        return jsonify({
            "error": "Einstiege vorübergehend eingefroren. Jemand sieht den Preis ein.",
            "frozen": True,
            "seconds_left": auction.freeze_seconds_left()
        }), 423

    entry_price = auction.starting_price * 0.01

    # with_for_update() блокує рядок на час транзакції → захист від race condition
    participant = AuctionParticipant.query.filter_by(
        auction_id=auction.id, user_id=current_user.id
    ).with_for_update().first()
    if not participant:
        participant = AuctionParticipant(auction_id=auction.id, user_id=current_user.id)
        db.session.add(participant)
    elif participant.has_paid_entry:
        return jsonify({"error": "Sie haben bereits an dieser Auktion teilgenommen."}), 400

    try:
        if ss.is_configured():
            # Вхід = гроші продавцю → ескроу (off-session списання зі збереженої картки)
            if not current_user.default_payment_method:
                return jsonify({"error": "Bitte hinterlegen Sie zuerst eine Karte für Einstiege.", "need_card": True}), 402
            try:
                pi = ss.charge_off_session(current_user, entry_price, auction.id, 'entry_fee')
            except stripe.error.CardError as e:
                return jsonify({"error": f"Zahlung abgelehnt: {getattr(e, 'user_message', None) or 'Karte abgelehnt'}"}), 402
            except Exception as e:
                print(f"Stripe entry error: {e}")
                return jsonify({"error": "Zahlungsfehler. Bitte erneut versuchen."}), 502
            participant.entry_payment_intent_id = pi.id
            participant.entry_amount = (participant.entry_amount or 0) + entry_price
            db.session.add(Transaction(type='entry_fee', user_id=current_user.id, auction_id=auction.id,
                                       amount_eur=entry_price, stripe_id=pi.id, status='succeeded'))
        else:
            # Dev/demo fallback: внутрішній баланс
            if current_user.balance < entry_price:
                return jsonify({"error": "Nicht genügend Guthaben"}), 400
            current_user.deduct_balance(entry_price)
            participant.entry_amount = (participant.entry_amount or 0) + entry_price

        participant.has_paid_entry = True
        auction.total_participants += 1
        auction.decrease_price(entry_price)  # Зменшуємо поточну ціну після участі
        auction.freeze()  # Заморожуємо нові входи на 5 сек

        db.session.commit()

        # Auto-Abschluss bei Preis 0 → der letzte Teilnehmer gewinnt → Benachrichtigungen
        if not auction.is_active:
            if not auction.winner_id:
                auction.winner_id = current_user.id
                db.session.commit()
            notify_auction_end(auction, current_user)

        return jsonify({
            "message": "Erfolgreich teilgenommen!",
            "participants": auction.total_participants,
            "final_price": auction.current_price
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Teilnahmefehler: {e}")
        return jsonify({"error": "Teilnahme fehlgeschlagen"}), 500

@user_bp.route('/close_auction/<int:auction_id>', methods=['POST'])
@login_required
def close_auction(auction_id):
    auction = Auction.query.get(auction_id)
    if not auction:
        flash("Auktion nicht gefunden.", "error")
        return redirect(url_for('user.buyer_dashboard', email=current_user.email))

    if not auction.is_active:
        flash("Auktion ist bereits beendet.", "info")
        return redirect(url_for('user.buyer_dashboard', email=current_user.email))

    participant = AuctionParticipant.query.filter_by(auction_id=auction.id, user_id=current_user.id).first()
    if not participant or not participant.has_paid_entry:
        flash("Sie können diese Auktion nicht abschließen, da Sie nicht teilgenommen haben.", "error")
        return redirect(url_for('user.buyer_dashboard', email=current_user.email))

    closing_price = auction.current_price
    try:
        if ss.is_configured():
            # Закриття = решта ціни → ескроу (off-session). Виплата продавцю — при підтвердженні отримання.
            if not current_user.default_payment_method:
                flash("Bitte hinterlegen Sie zuerst eine Karte in Ihrem Konto.", "error")
                return redirect(url_for('user.buyer_dashboard', email=current_user.email))
            if closing_price > 0:
                try:
                    pi = ss.charge_off_session(current_user, closing_price, auction.id, 'closing_payment')
                except stripe.error.CardError as e:
                    flash(f"Zahlung abgelehnt: {getattr(e, 'user_message', None) or 'Karte abgelehnt'}", "error")
                    return redirect(url_for('user.buyer_dashboard', email=current_user.email))
                except Exception as e:
                    print(f"Stripe closing error: {e}")
                    flash("Zahlungsfehler beim Abschluss. Bitte erneut versuchen.", "error")
                    return redirect(url_for('user.buyer_dashboard', email=current_user.email))
                db.session.add(Transaction(type='closing_payment', user_id=current_user.id, auction_id=auction.id,
                                           amount_eur=closing_price, stripe_id=pi.id, status='succeeded'))
        else:
            # Dev/demo fallback: внутрішній баланс
            if current_user.balance < closing_price:
                flash("Nicht genügend Guthaben zum Abschluss der Auktion.", "error")
                return redirect(url_for('user.buyer_dashboard', email=current_user.email))
            current_user.deduct_balance(closing_price)

        auction.close_auction(winner_id=current_user.id)
        notify_auction_end(auction, current_user)
        flash("Auktion erfolgreich abgeschlossen! Sie erhalten eine E-Mail mit den Kontaktdaten des Verkäufers. "
              "Bestätigen Sie den Erhalt, damit der Verkäufer ausgezahlt wird.", "success")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Auktion schließen Fehler (auction_id={auction_id}): {e}")
        flash("Auktion konnte nicht abgeschlossen werden. Bitte später erneut versuchen.", "error")
    return redirect(url_for('user.buyer_dashboard', email=current_user.email))

@user_bp.route('/confirm_receive/<int:auction_id>', methods=['POST'])
@login_required
def confirm_receive(auction_id):
    auction = Auction.query.get(auction_id)
    if not auction or not auction.winner_id or auction.winner_id != current_user.id:
        flash("Sie sind nicht der Gewinner dieser Auktion oder die Auktion wurde nicht gefunden.", "error")
        return redirect(url_for('user.buyer_dashboard', email=current_user.email))
    if auction.is_confirmed:
        flash("Sie haben den Erhalt bereits bestätigt.", "info")
        return redirect(url_for('user.buyer_dashboard', email=current_user.email))
    try:
        seller = db.session.get(User, auction.seller_id)
        if ss.is_configured():
            # Сума виплати = всі входи + закриття (з ескроу) = ринкова ціна
            paid = db.session.query(db.func.coalesce(db.func.sum(Transaction.amount_eur), 0.0)).filter(
                Transaction.auction_id == auction.id,
                Transaction.type.in_(['entry_fee', 'closing_payment']),
                Transaction.status == 'succeeded'
            ).scalar() or 0.0

            if not seller or not seller.stripe_account_id or not seller.stripe_payouts_enabled:
                flash("Der Verkäufer hat Stripe-Auszahlungen noch nicht aktiviert. Das Geld bleibt im Treuhand.", "error")
                return redirect(url_for('user.buyer_dashboard', email=current_user.email))

            if paid > 0:
                try:
                    tr = ss.transfer_to_seller(seller.stripe_account_id, paid, auction.id)
                except Exception as e:
                    print(f"Stripe transfer error: {e}")
                    flash("Geld konnte nicht an den Verkäufer überwiesen werden. Bitte später erneut versuchen.", "error")
                    return redirect(url_for('user.buyer_dashboard', email=current_user.email))
                db.session.add(Transaction(type='transfer_seller', user_id=seller.id, auction_id=auction.id,
                                           amount_eur=paid, stripe_id=tr.id, status='succeeded'))
        else:
            # Dev/demo fallback: кредитуємо внутрішній баланс продавця
            if seller:
                total = auction.total_participants * auction.starting_price * 0.01 + auction.current_price
                seller.add_balance(total)

        auction.is_confirmed = True
        db.session.commit()
        flash("Erhalt bestätigt. Das Geld wurde an den Verkäufer überwiesen!", "success")
    except Exception as e:
        db.session.rollback()
        print(f"Fehler bei der Empfangsbestätigung: {e}")
        flash("Empfang konnte nicht bestätigt werden. Bitte später erneut versuchen.", "error")
    return redirect(url_for('user.buyer_dashboard', email=current_user.email))

@user_bp.route('/seller_profile', methods=['POST'])
@login_required
def save_seller_profile():
    """Öffentliche Profildaten des Verkäufers (Google-Link)."""
    if current_user.user_type != 'seller':
        flash("Nur Verkäufer.", "error")
        return redirect(url_for('main.index'))
    url = (request.form.get('google_business_url') or '').strip()
    if url and not (url.startswith('http://') or url.startswith('https://')):
        url = 'https://' + url
    current_user.google_business_url = url[:500] or None
    db.session.commit()
    flash("Profil aktualisiert.", "success")
    return redirect(url_for('user.seller_dashboard', email=current_user.email))


@user_bp.route('/confirm_listing/<int:auction_id>', methods=['POST'])
@login_required
def confirm_listing(auction_id):
    """Verkäufer bestätigt die Echtheit seines Inserats (ohne Einsicht in Preis/Teilnehmer)."""
    auction = Auction.query.get(auction_id)
    if not auction or auction.seller_id != current_user.id:
        flash("Auktion nicht gefunden.", "error")
        return redirect(url_for('user.seller_dashboard', email=current_user.email))
    auction.seller_confirmed = True
    db.session.commit()
    flash("Echtheit des Inserats bestätigt.", "success")
    return redirect(url_for('user.seller_dashboard', email=current_user.email))


@user_bp.route('/review/<int:auction_id>', methods=['POST'])
@login_required
def submit_review(auction_id):
    """Verkäuferbewertung — nur vom Gewinner einer bestätigten Auktion."""
    from app.models.review import Review
    from app.ai import moderation
    from app.services.rating import recompute_seller_rating

    auction = Auction.query.get(auction_id)
    if not auction or auction.winner_id != current_user.id or not auction.is_confirmed:
        flash("Bewertung nur nach bestätigtem Kauf möglich.", "error")
        return redirect(url_for('user.buyer_dashboard', email=current_user.email))

    if Review.query.filter_by(auction_id=auction_id, reviewer_id=current_user.id).first():
        flash("Sie haben diese Auktion bereits bewertet.", "info")
        return redirect(url_for('user.buyer_dashboard', email=current_user.email))

    try:
        stars = int(request.form.get('stars', 0))
    except ValueError:
        stars = 0
    if stars < 1 or stars > 5:
        flash("Bitte eine Bewertung von 1 bis 5 Sternen wählen.", "error")
        return redirect(url_for('user.buyer_dashboard', email=current_user.email))

    text = (request.form.get('text') or '').strip()[:1000]
    # KI-Prüfung auf Echtheit/Zulässigkeit
    check = moderation.check_review(text)
    status = 'approved' if check.get('ok', True) else 'flagged'

    db.session.add(Review(seller_id=auction.seller_id, reviewer_id=current_user.id,
                          auction_id=auction_id, stars=stars, text=text, status=status))
    db.session.commit()
    recompute_seller_rating(auction.seller_id)

    if status == 'flagged':
        flash("Danke! Ihre Bewertung wird geprüft (mögliche unzulässige Inhalte).", "info")
    else:
        flash("Danke für Ihre Bewertung!", "success")
    return redirect(url_for('user.buyer_dashboard', email=current_user.email))


@user_bp.route('/tax_info', methods=['POST'])
@login_required
def save_tax_info():
    """DAC7/PStTG — Steuerdaten des Verkäufers speichern."""
    if current_user.user_type != 'seller':
        flash("Nur Verkäufer.", "error")
        return redirect(url_for('main.index'))
    current_user.seller_type = request.form.get('seller_type') or None
    current_user.tax_id = request.form.get('tax_id') or None
    current_user.address = request.form.get('address') or None
    current_user.country = (request.form.get('country') or '').upper()[:2] or None
    current_user.date_of_birth = request.form.get('date_of_birth') or None
    # Pflichtfelder je nach Typ
    required = current_user.seller_type and current_user.tax_id and current_user.address and current_user.country
    if current_user.seller_type == 'private':
        required = required and current_user.date_of_birth
    current_user.dac7_complete = bool(required)
    db.session.commit()
    flash("Steuerangaben gespeichert." if current_user.dac7_complete
          else "Steuerangaben gespeichert (unvollständig — bitte alle Pflichtfelder ausfüllen).",
          "success" if current_user.dac7_complete else "info")
    return redirect(url_for('user.seller_dashboard', email=current_user.email))


@user_bp.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    """GDPR Art. 17 — Recht auf Löschung. Anonymisiert das Konto (Transaktions-/
    Steuerdaten bleiben aus gesetzlichen Gründen erhalten). Blockiert bei offenen
    Verpflichtungen (aktive Auktionen / unbestätigte Gewinne / offener Treuhand)."""
    user = current_user

    # Offene Verpflichtungen prüfen
    active_as_seller = Auction.query.filter_by(seller_id=user.id, is_active=True).count()
    unconfirmed_won = Auction.query.filter_by(winner_id=user.id, is_active=False, is_confirmed=False).count()
    if active_as_seller or unconfirmed_won:
        flash("Konto kann nicht gelöscht werden: Sie haben noch offene Auktionen oder "
              "unbestätigte Käufe (Treuhand). Bitte schließen Sie diese zuerst ab.", "error")
        return redirect(url_for('user.buyer_dashboard', email=user.email)
                        if user.user_type == 'buyer'
                        else url_for('user.seller_dashboard', email=user.email))

    try:
        # Відкликати Stripe ресурси до анонімізації
        if ss.is_configured():
            try:
                import stripe as _stripe
                _stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
                if user.default_payment_method:
                    _stripe.PaymentMethod.detach(user.default_payment_method)
                if user.stripe_customer_id:
                    _stripe.Customer.delete(user.stripe_customer_id)
            except Exception as stripe_err:
                current_app.logger.warning(f"Stripe cleanup on delete: {stripe_err}")

        # Anonymisierung der personenbezogenen Daten (PII)
        uid = user.id
        user.username = f"geloeschter_nutzer_{uid}"
        user.email = f"deleted_{uid}@deleted.local"
        user.set_password(secrets.token_urlsafe(24))
        user.wallet_address = None
        user.stripe_customer_id = None
        user.stripe_account_id = None
        user.default_payment_method = None
        user.service_credits = 0
        user.is_deleted = True
        db.session.commit()
        logout_user()
        flash("Ihr Konto wurde gelöscht. Persönliche Daten wurden anonymisiert. "
              "Transaktionsbelege bleiben aus gesetzlichen Gründen (Steuer) erhalten.", "success")
        return redirect(url_for('main.index'))
    except Exception as e:
        db.session.rollback()
        print(f"Account deletion error: {e}")
        flash("Konto konnte nicht gelöscht werden. Bitte später erneut versuchen.", "error")
        return redirect(url_for('main.index'))


@user_bp.route('/connect_wallet', methods=['POST'])
@login_required
def connect_wallet():
    wallet_address = request.form.get('wallet_address')
    if not wallet_address:
        return jsonify({'error': 'Keine Wallet-Adresse angegeben'}), 400
    current_user.wallet_address = wallet_address
    db.session.commit()
    return jsonify({'message': 'Wallet verbunden!'}), 200

