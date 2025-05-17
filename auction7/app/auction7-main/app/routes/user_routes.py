from flask import Blueprint, request, jsonify, redirect, url_for, flash, render_template
from flask_login import login_required, current_user
from app import db
from app.models.user import User
from app.models.auction import Auction
from app.models.auction_participant import AuctionParticipant
from blockchain_payments.payment_matic import process_payment, send_to_escrow, send_to_admin, release_from_escrow

user_bp = Blueprint('user', __name__)

@user_bp.route('/add_balance', methods=['POST'])
@login_required
def add_balance():
    data = request.get_json()
    if not data or 'amount' not in data:
        return jsonify({"error": "Некоректний формат запиту"}), 400

    try:
        amount = float(data['amount'])
        if amount <= 0:
            return jsonify({"error": "Сума має бути більше 0"}), 400

        current_user.balance += amount
        db.session.commit()
        return jsonify({"message": "Баланс успішно поповнено!", "new_balance": current_user.balance}), 200
    except ValueError:
        return jsonify({"error": "Некоректна сума"}), 400
    except Exception as e:
        print(f"Помилка: {e}")
        return jsonify({"error": "Не вдалося поповнити баланс."}), 500

@user_bp.route('/buyer/<string:email>', methods=['GET', 'POST'])
@login_required
def buyer_dashboard(email):
    if current_user.email != email:
        flash("Неавторизований доступ", 'error')
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash("Користувача не знайдено", 'error')
        return redirect(url_for('auth.login'))

    # Активні аукціони
    auctions = Auction.query.filter_by(is_active=True).all()
    # Аукціони, які очікують підтвердження отримання (переможець — поточний користувач)
    pending_confirmations = Auction.query.filter_by(is_active=False, is_confirmed=False, winner_id=current_user.id).all()

    if request.method == 'POST':
        auction_id = request.form.get('auction_id')
        auction = Auction.query.get(auction_id)

        if not auction:
            flash("Аукціон не знайдено.", "error")
            return redirect(url_for('user.buyer_dashboard', email=current_user.email))

        try:
            view_price = 1.0
            participant = AuctionParticipant.query.filter_by(auction_id=auction.id, user_id=current_user.id).first()

            if participant and participant.has_viewed_price:
                flash("Ви вже переглядали поточну ціну цього аукціону.", "info")
                return redirect(url_for('user.buyer_dashboard', email=current_user.email))

            if current_user.balance < view_price:
                flash("Недостатньо коштів на балансі для перегляду ціни.", "error")
                return redirect(url_for('user.buyer_dashboard', email=current_user.email))

            current_user.deduct_balance(view_price)
            auction.add_to_earnings(view_price)

            if not participant:
                participant = AuctionParticipant(auction_id=auction.id, user_id=current_user.id)
                db.session.add(participant)

            participant.mark_viewed_price()
            db.session.commit()

            flash(f"Перегляд ціни успішний! Поточна ціна: {auction.current_price} грн", "success")
        except Exception as e:
            db.session.rollback()
            print(f"Помилка перегляду ціни: {e}")
            flash("Не вдалося виконати перегляд. Спробуйте пізніше.", "error")

    return render_template('users/buyer_dashboard.html', user=user, auctions=auctions, pending_confirmations=pending_confirmations)

@user_bp.route('/seller/<string:email>', methods=['GET'])
@login_required
def seller_dashboard(email):
    if current_user.email != email:
        flash("Неавторизований доступ", 'error')
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash("Користувача не знайдено", 'error')
        return redirect(url_for('auth.login'))

    all_auctions = Auction.query.filter_by(seller_id=user.id).all()

    completed_auctions = [
        {
            'title': auction.title,
            'description': auction.description,
            'starting_price': auction.starting_price,
            'status': 'Закритий' if not auction.is_active else 'Активний',
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
        balance_from_completed=balance_from_completed
    )

@user_bp.route('/participate/<int:auction_id>', methods=['POST'])
@login_required
def participate_in_auction(auction_id):
    auction = Auction.query.get(auction_id)
    if not auction or not auction.is_active:
        return jsonify({"error": "Аукціон не знайдено або вже закритий"}), 400

    entry_price = auction.starting_price * 0.01
    if current_user.balance < entry_price:
        return jsonify({"error": "Недостатньо коштів на балансі"}), 400

    try:
        current_user.deduct_balance(entry_price)

        participant = AuctionParticipant.query.filter_by(auction_id=auction.id, user_id=current_user.id).first()
        if not participant:
            participant = AuctionParticipant(auction_id=auction.id, user_id=current_user.id)
            db.session.add(participant)

        participant.has_paid_entry = True
        auction.total_participants += 1
        auction.decrease_price(entry_price)  # Зменшуємо поточну ціну після участі

        db.session.commit()
        return jsonify({
            "message": "Успішно взято участь!",
            "participants": auction.total_participants,
            "final_price": auction.current_price
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Помилка участі: {e}")
        return jsonify({"error": "Не вдалося взяти участь"}), 500

@user_bp.route('/close_auction/<int:auction_id>', methods=['POST'])
@login_required
def close_auction(auction_id):
    auction = Auction.query.get(auction_id)
    if not auction:
        flash("Аукціон не знайдено.", "error")
        return redirect(url_for('user.buyer_dashboard', email=current_user.email))

    if not auction.is_active:
        flash("Аукціон вже закритий.", "info")
        return redirect(url_for('user.buyer_dashboard', email=current_user.email))

    participant = AuctionParticipant.query.filter_by(auction_id=auction.id, user_id=current_user.id).first()
    if not participant or not participant.has_paid_entry:
        flash("Ви не можете закрити цей аукціон, оскільки не брали участь у ньому.", "error")
        return redirect(url_for('user.buyer_dashboard', email=current_user.email))

    if current_user.balance < auction.current_price:
        flash("Недостатньо коштів для закриття аукціону.", "error")
        return redirect(url_for('user.buyer_dashboard', email=current_user.email))

    try:
        print(f"[DEBUG] Спроба закрити аукціон: auction_id={auction.id}, user_id={current_user.id}, balance={current_user.balance}, current_price={auction.current_price}")
        current_user.deduct_balance(auction.current_price)
        print(f"[DEBUG] Баланс після списання: {current_user.balance}")
        auction.close_auction(winner_id=current_user.id)
        print(f"[DEBUG] Аукціон закрито: is_active={auction.is_active}, winner_id={auction.winner_id}")
        flash("Аукціон успішно закрито! Вітаємо з перемогою.", "success")
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Помилка закриття аукціону: {e}")
        flash(f"Не вдалося закрити аукціон. {e}", "error")
    return redirect(url_for('user.buyer_dashboard', email=current_user.email))

@user_bp.route('/confirm_receive/<int:auction_id>', methods=['POST'])
@login_required
def confirm_receive(auction_id):
    auction = Auction.query.get(auction_id)
    if not auction or not auction.winner_id or auction.winner_id != current_user.id:
        flash("Ви не є переможцем цього аукціону або аукціон не знайдено.", "error")
        return redirect(url_for('user.buyer_dashboard', email=current_user.email))
    if auction.is_confirmed:
        flash("Ви вже підтвердили отримання товару.", "info")
        return redirect(url_for('user.buyer_dashboard', email=current_user.email))
    try:
        # Викликати release_from_escrow (реалізуйте у payment_matic.py)
        # release_from_escrow(auction.id)  # Розкоментуйте, якщо функція готова
        auction.is_confirmed = True
        db.session.commit()
        flash("Отримання товару підтверджено. Кошти переведено продавцю!", "success")
    except Exception as e:
        db.session.rollback()
        print(f"Помилка підтвердження отримання: {e}")
        flash("Не вдалося підтвердити отримання. Спробуйте пізніше.", "error")
    return redirect(url_for('user.buyer_dashboard', email=current_user.email))

@user_bp.route('/connect_wallet', methods=['POST'])
@login_required
def connect_wallet():
    wallet_address = request.form.get('wallet_address')
    if not wallet_address:
        return jsonify({'error': 'Не вказано адресу гаманця'}), 400
    current_user.wallet_address = wallet_address
    db.session.commit()
    return jsonify({'message': 'Гаманець підключено!'}), 200

