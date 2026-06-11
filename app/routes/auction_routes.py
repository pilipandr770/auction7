from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, Response, stream_with_context, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import uuid
import json
import time
from app import db, limiter
from app.models.auction import Auction
from app.models.user import User
from app.models.auction_participant import AuctionParticipant
from app.models.transaction import Transaction
from app.ai import moderation
from app.models.report import Report

auction_bp = Blueprint('auction', __name__)


@auction_bp.route('/<int:auction_id>/report', methods=['POST'])
def report_auction(auction_id):
    """DSA Notice-and-Action — Inserat melden (auch anonym möglich)."""
    auction = Auction.query.get(auction_id)
    if not auction:
        return jsonify({"error": "Auktion nicht gefunden"}), 404
    if request.is_json:
        reason = (request.json or {}).get('reason', '')
    else:
        reason = request.form.get('reason', '')
    if not reason:
        return jsonify({"error": "Bitte geben Sie einen Grund an"}), 400
    reporter_id = current_user.id if current_user.is_authenticated else None
    db.session.add(Report(auction_id=auction_id, reason=reason[:500], reporter_id=reporter_id))
    db.session.commit()
    return jsonify({"message": "Meldung eingegangen. Vielen Dank — wir prüfen das Inserat."}), 200


@auction_bp.route('/<int:auction_id>/stream')
@login_required
def auction_stream(auction_id):
    """Server-Sent Events: транслює ПУБЛІЧНИЙ стан аукціону (статус, заморозка).
    Поточна ціна та кількість учасників НЕ транслюються — це таємниця."""
    app = current_app._get_current_object()

    @stream_with_context
    def gen():
        last_payload = None
        while True:
            with app.app_context():
                auction = db.session.get(Auction, auction_id)
                if not auction:
                    yield f"data: {json.dumps({'exists': False})}\n\n"
                    break
                data = {
                    'exists': True,
                    'is_active': auction.is_active,
                    'frozen': auction.is_frozen(),
                    'seconds_left': auction.freeze_seconds_left(),
                }
                db.session.remove()  # свіже читання на наступній ітерації
            payload = json.dumps(data)
            # надсилаємо лише коли стан змінився або щоб тримати з'єднання живим
            yield f"data: {payload}\n\n"
            last_payload = payload
            time.sleep(2)

    return Response(gen(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_MIMETYPES = {'image/png', 'image/jpeg', 'image/gif'}
UPLOAD_FOLDER = os.path.join('app', 'static', 'images', 'uploads')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(file):
    """Перевіряє розширення І MIME-тип файлу."""
    filename = file.filename
    ext_ok = '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    mime_ok = file.mimetype in ALLOWED_MIMETYPES
    return ext_ok and mime_ok

@auction_bp.route('/create', methods=['POST'])
@login_required
def create_auction():
    if current_user.user_type != 'seller':
        flash("Nur Verkäufer können Auktionen erstellen.", "error")
        return redirect(url_for('user.seller_dashboard', email=current_user.email))

    title = request.form.get('title')
    description = request.form.get('description')
    starting_price = request.form.get('starting_price')
    market_reference = request.form.get('market_reference') or None
    if market_reference and not (market_reference.startswith('http://') or market_reference.startswith('https://')):
        flash("Marktpreis-Link muss mit http:// oder https:// beginnen.", "error")
        return redirect(url_for('user.seller_dashboard', email=current_user.email))

    if not title or not description or not starting_price:
        flash("Alle Felder sind erforderlich.", "error")
        return redirect(url_for('user.seller_dashboard', email=current_user.email))

    # Plattform-Regel: nur NEUE und unbenutzte Artikel
    if not request.form.get('condition_new'):
        flash("Nur neue und unbenutzte Artikel sind erlaubt. Bitte bestätigen Sie dies.", "error")
        return redirect(url_for('user.seller_dashboard', email=current_user.email))

    try:
        starting_price = float(starting_price)
    except ValueError:
        flash("Der Preis muss eine Zahl sein.", "error")
        return redirect(url_for('user.seller_dashboard', email=current_user.email))

    # Перевірка ринкової ціни: має бути актуальною та не завищеною
    MIN_PRICE = 1.0
    MAX_PRICE = 1_000_000.0
    if starting_price < MIN_PRICE:
        flash(f"Der Startpreis muss mindestens {MIN_PRICE:.0f} € betragen.", "error")
        return redirect(url_for('user.seller_dashboard', email=current_user.email))
    if starting_price > MAX_PRICE:
        flash(f"Der Startpreis ist zu hoch (maximal {MAX_PRICE:.0f} €). Geben Sie den aktuellen Marktpreis an.", "error")
        return redirect(url_for('user.seller_dashboard', email=current_user.email))

    # KI-Moderation des Inserats (verbotene Artikel blockieren, Verdacht markieren)
    mod = moderation.moderate_listing(title, description, starting_price)
    if mod['status'] == moderation.REJECT:
        flash(f"Inserat abgelehnt: {mod.get('reason') or 'verbotener Artikel'}.", "error")
        return redirect(url_for('user.seller_dashboard', email=current_user.email))

    # Завантаження фотографій
    photos = []
    if 'photos' in request.files:
        files = request.files.getlist('photos')
        for file in files:
            if file and allowed_file(file):
                ext = secure_filename(file.filename).rsplit('.', 1)[1].lower()
                filename = f"{uuid.uuid4().hex}.{ext}"  # UUID → no collisions, no path traversal
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                photos.append(f"images/uploads/{filename}")

    try:
        new_auction = Auction(
            title=title,
            description=description,
            starting_price=starting_price,
            seller_id=current_user.id,
            photos=photos,
            market_reference=market_reference
        )
        new_auction.moderation_status = mod['status']
        new_auction.moderation_reason = mod.get('reason')
        db.session.add(new_auction)
        db.session.commit()

        if mod['status'] == moderation.FLAG:
            flash("Auktion erstellt, wird aber zur Prüfung markiert (Verdachtssignale).", "info")
        elif mod['status'] == moderation.PENDING:
            flash("Auktion erstellt. Sie wird vom Administrator geprüft.", "info")
        else:
            flash("Auktion erfolgreich erstellt!", "success")
    except Exception as e:
        db.session.rollback()
        print(f"Fehler beim Erstellen der Auktion: {e}")
        flash("Auktion konnte nicht erstellt werden. Bitte später erneut versuchen.", "error")

    return redirect(url_for('user.seller_dashboard', email=current_user.email))

@auction_bp.route('/<int:auction_id>', methods=['GET'])
@login_required
def auction_detail(auction_id):
    auction = Auction.query.get(auction_id)
    if not auction:
        flash("Auktion nicht gefunden.", 'error')
        return redirect(url_for('main.index'))
    return render_template('auctions/auction_detail.html', auction=auction)

@auction_bp.route('/view/<int:auction_id>', methods=['POST'])
@login_required
@limiter.limit("20 per minute")
def view_auction(auction_id):
    auction = Auction.query.get(auction_id)
    if not auction:
        return jsonify({"error": "Auktion nicht gefunden"}), 404

    if not auction.is_active:
        return jsonify({"error": "Auktion ist bereits beendet"}), 400

    # Перевіряємо, чи користувач є учасником аукціону
    participant = AuctionParticipant.query.filter_by(auction_id=auction_id, user_id=current_user.id).first()
    if not participant or not participant.has_paid_entry:
        return jsonify({"error": "Sie müssen teilnehmen, um diese Information einzusehen"}), 403

    try:
        # Перегляд коштує 1 сервіс-кредит (передоплачені, дохід платформи отримано при покупці)
        if (current_user.service_credits or 0) < 1:
            return jsonify({
                "error": "Nicht genügend Kredite. Bitte laden Sie Einsicht-Kredite auf.",
                "no_credits": True
            }), 402

        current_user.service_credits -= 1
        db.session.add(Transaction(type='view_fee', user_id=current_user.id,
                                   auction_id=auction.id, credits_delta=-1,
                                   status='succeeded'))

        # Позначаємо факт перегляду (для статистики) — не блокує повторні перегляди
        participant.has_viewed_price = True

        # Заморожуємо нові входи на 5 сек — даємо час прийняти рішення
        auction.freeze()

        db.session.commit()

        return jsonify({
            "message": "Einsicht aktualisiert",
            "participants": auction.total_participants,
            "final_price": round(auction.current_price, 2),
            "credits_left": current_user.service_credits,
            "freeze_seconds": auction.freeze_seconds_left()
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Fehler bei der Auktions-Einsicht: {e}")
        return jsonify({"error": "Einsicht konnte nicht aktualisiert werden"}), 500


