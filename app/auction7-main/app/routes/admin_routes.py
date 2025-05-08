from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models.user import User
from app.models.auction import Auction

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard', methods=['GET'])
@login_required
def admin_dashboard():
    # Перевірка, чи є користувач адміністратором
    if not current_user.is_admin:
        return "Доступ заборонено", 403

    # Отримання списку користувачів та аукціонів
    users = User.query.all()
    auctions = Auction.query.all()

    # Розрахунок загального балансу адміністратора
    admin_balance = current_user.balance  # Поточний баланс адміністратора

    # Відображення панелі адміністратора
    return render_template('admin/dashboard.html', 
                           users=users, 
                           auctions=auctions, 
                           admin_balance=admin_balance)
