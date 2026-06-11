from flask import Blueprint, render_template, Response, request
from flask_login import login_required, current_user
from datetime import datetime
import csv
import io
from app.models.user import User
from app.models.auction import Auction

admin_bp = Blueprint('admin', __name__)

# DAC7-Schwellen (Verkauf von Waren): Meldung ab 30 Verkäufen ODER 2.000 € Umsatz
DAC7_MIN_SALES = 30
DAC7_MIN_AMOUNT = 2000.0


@admin_bp.route('/dac7_export', methods=['GET'])
@login_required
def dac7_export():
    """DAC7/PStTG — CSV-Export der meldepflichtigen Verkäufer für ein Jahr."""
    if not current_user.is_admin:
        return "Zugriff verweigert", 403

    try:
        year = int(request.args.get('year', datetime.utcnow().year))
    except ValueError:
        year = datetime.utcnow().year

    # Verkäufe = abgeschlossene & bestätigte Auktionen im Jahr
    sellers = {}
    auctions = Auction.query.filter_by(is_active=False, is_confirmed=True).all()
    for au in auctions:
        ref = au.updated_at or au.created_at
        if not ref or ref.year != year:
            continue
        s = sellers.setdefault(au.seller_id, {'count': 0, 'amount': 0.0})
        s['count'] += 1
        s['amount'] += au.starting_price  # Verkäufer erhält den Marktpreis

    output = io.StringIO()
    w = csv.writer(output, delimiter=';')
    w.writerow(['seller_id', 'name', 'email', 'seller_type', 'tax_id', 'address',
                'country', 'date_of_birth', 'sales_count', 'total_amount_eur',
                'reportable', 'dac7_data_complete'])
    for sid, agg in sellers.items():
        u = User.query.get(sid)
        if not u:
            continue
        reportable = agg['count'] >= DAC7_MIN_SALES or agg['amount'] >= DAC7_MIN_AMOUNT
        w.writerow([sid, u.username, u.email, u.seller_type or '', u.tax_id or '',
                    u.address or '', u.country or '', u.date_of_birth or '',
                    agg['count'], round(agg['amount'], 2),
                    'JA' if reportable else 'nein',
                    'JA' if u.dac7_complete else 'NEIN'])

    csv_data = output.getvalue()
    return Response(csv_data, mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename=dac7_report_{year}.csv'})

@admin_bp.route('/dashboard', methods=['GET'])
@login_required
def admin_dashboard():
    # Перевірка, чи є користувач адміністратором
    if not current_user.is_admin:
        return "Zugriff verweigert", 403

    # Отримання списку користувачів та аукціонів
    users = User.query.all()
    auctions = Auction.query.all()
    admin_balance = current_user.balance

    from app.models.report import Report
    reports = Report.query.order_by(Report.created_at.desc()).all()
    auction_titles = {a.id: a.title for a in auctions}

    return render_template('admin/dashboard.html',
                           users=users,
                           auctions=auctions,
                           admin_balance=admin_balance,
                           reports=reports,
                           auction_titles=auction_titles)
