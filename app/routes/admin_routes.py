from flask import Blueprint, render_template, flash, redirect, url_for  # add flash, redirect, url_for
from flask_login import login_required, current_user
from app.models.user import User
from app.models.auction import Auction
from app import db  # add db import

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

@admin_bp.route('/en/dashboard', methods=['GET'])
@login_required
def admin_dashboard_en():
    if not current_user.is_admin:
        return "Access denied", 403
    users = User.query.all()
    auctions = Auction.query.all()
    admin_balance = current_user.balance
    return render_template('admin/dashboard_en.html', users=users, auctions=auctions, admin_balance=admin_balance)

@admin_bp.route('/de/dashboard', methods=['GET'])
@login_required
def admin_dashboard_de():
    if not current_user.is_admin:
        return "Zugriff verweigert", 403
    users = User.query.all()
    auctions = Auction.query.all()
    admin_balance = current_user.balance
    return render_template('admin/dashboard_de.html', users=users, auctions=auctions, admin_balance=admin_balance)

@admin_bp.route('/verify_sellers', methods=['GET', 'POST'])
@login_required
def verify_sellers():
    if not current_user.is_admin:
        return "Доступ заборонено", 403

    unverified_sellers = User.query.filter_by(user_type='seller', is_verified=False).all()

    return render_template('admin/verify_sellers.html', sellers=unverified_sellers)

@admin_bp.route('/en/verify_sellers', methods=['GET', 'POST'])
@login_required
def verify_sellers_en():
    if not current_user.is_admin:
        return "Access denied", 403
    unverified_sellers = User.query.filter_by(user_type='seller', is_verified=False).all()
    return render_template('admin/verify_sellers_en.html', sellers=unverified_sellers)

@admin_bp.route('/de/verify_sellers', methods=['GET', 'POST'])
@login_required
def verify_sellers_de():
    if not current_user.is_admin:
        return "Zugriff verweigert", 403
    unverified_sellers = User.query.filter_by(user_type='seller', is_verified=False).all()
    return render_template('admin/verify_sellers_de.html', sellers=unverified_sellers)

@admin_bp.route('/verify_seller/<int:user_id>', methods=['POST'])
@login_required
def verify_seller_action(user_id):
    if not current_user.is_admin:
        return "Доступ заборонено", 403

    seller = User.query.get(user_id)
    if not seller or seller.user_type != 'seller':
        flash("Продавця не знайдено", "error")
        return redirect(url_for('admin.verify_sellers'))

    try:
        seller.is_verified = True
        db.session.commit()
        flash(f"Продавець {seller.username} підтверджений", "success")
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Seller verification failed: {e}")
        flash(f"Помилка підтвердження продавця: {e}", "error")
    return redirect(url_for('admin.verify_sellers'))
