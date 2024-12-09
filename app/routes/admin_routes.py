from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from app.models.user import User
from app.models.auction import Auction

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard', methods=['GET'])
@login_required
def admin_dashboard():
    # Перевірка, чи користувач є адміністратором
    if not current_user.is_admin:
        return redirect(url_for('auth.login'))

    # Отримання списку користувачів та аукціонів
    users = User.query.all()
    auctions = Auction.query.all()
    
    return render_template('admin/dashboard.html', users=users, auctions=auctions)
