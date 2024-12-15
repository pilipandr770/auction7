from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from app import db
from app.models.auction import Auction
from app.models.user import User
from app.models.auction_participant import AuctionParticipant

auction_bp = Blueprint('auction', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
UPLOAD_FOLDER = os.path.join('app', 'static', 'images', 'uploads')

# Створення папки для завантаження фотографій, якщо вона не існує
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@auction_bp.route('/create', methods=['POST'])
@login_required
def create_auction():
    if current_user.user_type != 'seller':
        flash("Тільки продавці можуть створювати аукціони.", "error")
        return redirect(url_for('user.seller_dashboard', email=current_user.email))

    title = request.form.get('title')
    description = request.form.get('description')
    starting_price = request.form.get('starting_price')

    if not title or not description or not starting_price:
        flash("Усі поля обов'язкові.", "error")
        return redirect(url_for('user.seller_dashboard', email=current_user.email))

    try:
        starting_price = float(starting_price)
    except ValueError:
        flash("Ціна повинна бути числом.", "error")
        return redirect(url_for('user.seller_dashboard', email=current_user.email))

    # Завантаження фотографій
    photos = []
    if 'photos' in request.files:
        files = request.files.getlist('photos')
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                photos.append(f"images/uploads/{filename}")

    try:
        new_auction = Auction(
            title=title,
            description=description,
            starting_price=starting_price,
            seller_id=current_user.id,
            photos=photos
        )
        db.session.add(new_auction)
        db.session.commit()

        flash("Аукціон успішно створено!", "success")
    except Exception as e:
        db.session.rollback()
        print(f"Помилка створення аукціону: {e}")
        flash("Не вдалося створити аукціон. Спробуйте пізніше.", "error")

    return redirect(url_for('user.seller_dashboard', email=current_user.email))

@auction_bp.route('/<int:auction_id>', methods=['GET', 'POST'])
@login_required
def auction_detail(auction_id):
    auction = Auction.query.get(auction_id)

    if not auction:
        flash("Аукціон не знайдено.", 'error')
        return redirect(url_for('auction.buyer_auctions'))

    if request.method == 'POST':
        try:
            entry_price = auction.starting_price * 0.01  # Вхідна ціна (1% від початкової ціни)
            participant = AuctionParticipant.query.filter_by(auction_id=auction_id, user_id=current_user.id).first()

            if participant and participant.has_paid_entry:
                return jsonify({"error": "Ви вже сплатили за участь в цьому аукціоні"}), 400

            if current_user.balance < entry_price:
                return jsonify({"error": "Недостатньо коштів на балансі"}), 400

            buyer = User.query.get(current_user.id)

            # Транзакція участі
            buyer.deduct_balance(entry_price)

            auction.total_participants += 1
            auction.current_price -= entry_price

            if auction.current_price <= 0:
                auction.current_price = 0
                auction.is_active = False  # Закриваємо аукціон

            if not participant:
                participant = AuctionParticipant(auction_id=auction_id, user_id=current_user.id)
                db.session.add(participant)

            participant.mark_paid_entry()

            db.session.commit()

            return jsonify({
                "message": "Успішно взято участь в аукціоні",
                "participants": auction.total_participants,
                "final_price": auction.current_price
            }), 200

        except Exception as e:
            db.session.rollback()
            print(f"Помилка участі в аукціоні: {e}")
            return jsonify({"error": "Не вдалося взяти участь в аукціоні"}), 500

    return render_template('auctions/auction_detail.html', auction=auction)

@auction_bp.route('/view/<int:auction_id>', methods=['POST'])
@login_required
def view_auction(auction_id):
    auction = Auction.query.get(auction_id)
    if not auction:
        return jsonify({"error": "Аукціон не знайдено"}), 404

    if not auction.is_active:
        return jsonify({"error": "Аукціон вже закритий"}), 400

    # Перевіряємо, чи користувач є учасником аукціону
    participant = AuctionParticipant.query.filter_by(auction_id=auction_id, user_id=current_user.id).first()
    if not participant or not participant.has_paid_entry:
        return jsonify({"error": "Ви повинні сплатити за участь, щоб переглянути цю інформацію"}), 403

    try:
        view_price = 1.0  # Вартість перегляду
        if participant.has_viewed_price:
            return jsonify({
                "message": "Ви вже переглядали поточну ціну",
                "participants": auction.total_participants,
                "final_price": auction.current_price
            }), 200

        # Перевірка балансу покупця
        if not current_user.can_afford(view_price):
            return jsonify({"error": "Недостатньо коштів на балансі для перегляду"}), 400

        # Списання коштів у покупця
        current_user.deduct_balance(view_price)

        # Знаходимо адміністратора
        admin = User.query.filter_by(is_admin=True).first()
        if admin:
            # Додаємо кошти на баланс адміністратора
            admin.add_balance(view_price)

        # Позначаємо, що користувач переглянув ціну
        participant.mark_viewed_price()

        # Фіксуємо зміни
        db.session.commit()

        return jsonify({
            "message": "Перегляд оновлений",
            "participants": auction.total_participants,
            "final_price": auction.current_price
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Помилка перегляду аукціону: {e}")
        return jsonify({"error": "Не вдалося оновити перегляд"}), 500


@auction_bp.route('/close/<int:auction_id>', methods=['POST'])
@login_required
def close_auction(auction_id):
    auction = Auction.query.get(auction_id)

    if not auction:
        flash("Аукціон не знайдено.", "error")
        return redirect(url_for('user.seller_dashboard', email=current_user.email))

    if not auction.is_active:
        flash("Цей аукціон вже закрито.", "info")
        return redirect(url_for('user.seller_dashboard', email=current_user.email))

    # Перевірка, чи користувач є учасником аукціону
    participant = AuctionParticipant.query.filter_by(auction_id=auction_id, user_id=current_user.id).first()
    if not participant or not participant.has_paid_entry:
        flash("Ви не можете закрити аукціон, оскільки не брали участь у ньому.", "error")
        return redirect(url_for('user.seller_dashboard', email=current_user.email))

    # Перевірка, чи у користувача достатньо коштів
    if current_user.balance < auction.current_price:
        flash("Недостатньо коштів для закриття аукціону.", "error")
        return redirect(url_for('user.seller_dashboard', email=current_user.email))

    try:
        buyer = current_user
        seller = User.query.get(auction.seller_id)

        # Списання коштів з балансу покупця
        buyer.deduct_balance(auction.current_price)

        # Додавання коштів на баланс продавця
        total_entry_payments = auction.total_participants * auction.starting_price * 0.01
        total_revenue = total_entry_payments + auction.current_price
        seller.add_balance(total_revenue)

        # Закриття аукціону
        auction.is_active = False
        auction.winner_id = buyer.id
        auction.total_earnings = total_revenue
        db.session.commit()

        # Відображення повідомлень
        if current_user.user_type == "seller":
            flash(f"Ваш товар продано. Покупець: {buyer.username}, Email: {buyer.email}.", "info")
            return redirect(url_for('user.seller_dashboard', email=current_user.email))

        if current_user.user_type == "buyer":
            flash(f"Ви виграли аукціон! Продавець: {seller.username}, Email: {seller.email}.", "info")
            return redirect(url_for('user.buyer_dashboard', email=current_user.email))

    except Exception as e:
        db.session.rollback()
        print(f"Помилка закриття аукціону: {e}")
        flash("Не вдалося закрити аукціон. Спробуйте пізніше.", "error")
        return redirect(url_for('user.seller_dashboard', email=current_user.email))
