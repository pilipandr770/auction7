from flask import Blueprint, request, jsonify, redirect, url_for, flash, render_template
from flask_login import login_required, current_user
from app import db
from app.models.user import User
from app.models.auction import Auction
from app.models.auction_participant import AuctionParticipant

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

    auctions = Auction.query.filter_by(is_active=True).all()

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

    return render_template('users/buyer_dashboard.html', user=user, auctions=auctions)

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
        total_entry_payments = auction.total_participants * auction.starting_price * 0.01
        total_revenue = total_entry_payments + auction.current_price

        current_user.deduct_balance(auction.current_price)
        seller = User.query.get(auction.seller_id)
        seller.add_balance(total_revenue)

        auction.close_auction(winner_id=current_user.id)
        db.session.commit()

        flash("Аукціон успішно закрито. Зв'яжіться з продавцем для отримання товару.", "success")
        return redirect(url_for('user.buyer_dashboard', email=current_user.email))

    except Exception as e:
        db.session.rollback()
        print(f"Помилка закриття аукціону: {e}")
        flash("Не вдалося закрити аукціон. Спробуйте пізніше.", "error")
        return redirect(url_for('user.buyer_dashboard', email=current_user.email))

@user_bp.route('/seller_contact/<int:seller_id>', methods=['GET'])
@login_required
def seller_contact(seller_id):
    """
    Відображає контактну інформацію продавця для покупця.
    """
    seller = User.query.get(seller_id)
    if not seller or seller.user_type != 'seller':
        flash("Продавця не знайдено.", "error")
        return redirect(url_for('user.buyer_dashboard', email=current_user.email))

    return render_template('users/seller_contact.html', seller=seller)

@user_bp.route("/connect_wallet", methods=["GET", "POST"])
@login_required
def connect_wallet():
    if request.method == "POST":
        wallet_address = request.form.get("wallet_address")
        if wallet_address and wallet_address.startswith("0x") and len(wallet_address) == 42:
            current_user.wallet_address = wallet_address
            db.session.commit()
            flash("Гаманець підключено успішно!", "success")
            return redirect(url_for("main.index"))
        else:
            flash("Некоректна адреса гаманця!", "danger")
    return render_template("connect_wallet.html")