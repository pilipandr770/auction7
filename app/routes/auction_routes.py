# routes/auction_routes.py
from flask import Blueprint, request, jsonify
from app.services.payment_service import PaymentService  # Імпортуємо клас PaymentService
from app.models.auction import Auction

auction_bp = Blueprint('auction', __name__)

@auction_bp.route('/create', methods=['POST'])
def create_auction():
    # Приклад створення нового аукціону
    data = request.get_json()
    auction_name = data.get('auction_name')
    start_price = data.get('start_price')

    new_auction = Auction(name=auction_name, start_price=start_price)
    # Зберігаємо аукціон у базі даних тут
    return jsonify({"message": f"Новий аукціон '{auction_name}' створено!"}), 201

@auction_bp.route('/pay_entry', methods=['POST'])
def pay_entry():
    data = request.get_json()
    user_email = data.get('user_email')
    auction_id = data.get('auction_id')
    amount = data.get('amount')

    response, status_code = PaymentService.process_entry_payment(user_email, auction_id, amount)
    return jsonify(response), status_code
