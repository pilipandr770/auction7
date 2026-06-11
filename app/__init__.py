from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
import os

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
limiter = Limiter(key_func=get_remote_address, default_limits=[])


def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html'), 500

    @app.errorhandler(Exception)
    def handle_exception(e):
        return render_template('errors/generic.html', error=e), 500


def create_app():
    app = Flask(__name__)

    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///auction.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    secret_key = os.getenv('SECRET_KEY', '')
    if not secret_key or secret_key == 'change-me-in-production':
        raise RuntimeError(
            "SECRET_KEY ist nicht gesetzt oder unsicher. "
            "Bitte setzen Sie SECRET_KEY in der .env-Datei auf einen zufälligen Wert."
        )
    app.config['SECRET_KEY'] = secret_key
    app.config['SESSION_PERMANENT'] = False
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

    # Stripe (платежі, Connect Express)
    app.config['STRIPE_SECRET_KEY'] = os.getenv('STRIPE_SECRET_KEY', '')
    app.config['STRIPE_PUBLISHABLE_KEY'] = os.getenv('STRIPE_PUBLISHABLE_KEY', '')
    app.config['STRIPE_WEBHOOK_SECRET'] = os.getenv('STRIPE_WEBHOOK_SECRET', '')
    app.config['APP_BASE_URL'] = os.getenv('APP_BASE_URL', 'http://127.0.0.1:5000')
    app.config['CREDIT_PRICE_EUR'] = float(os.getenv('CREDIT_PRICE_EUR', '1.0'))

    # E-Mail (SMTP)
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', '')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', '587'))
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', '')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '')
    app.config['MAIL_FROM'] = os.getenv('MAIL_FROM', '')
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
    app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'false').lower() == 'true'

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    limiter.init_app(app)
    login_manager.login_view = 'auth.login'

    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from app.models.auction import Auction
    from app.models.auction_participant import AuctionParticipant
    from app.models.payment import Payment
    from app.models.transaction import Transaction
    from app.models.report import Report
    from app.models.review import Review
    from app.verification.models import SellerVerification

    from app.routes.auth_routes import auth_bp
    from app.routes.user_routes import user_bp
    from app.routes.auction_routes import auction_bp
    from app.routes.main_routes import main_bp
    from app.routes.admin_routes import admin_bp
    from assistans.routes import assistant_bp
    from app.verification.routes import verification_bp
    from app.verification.admin_routes import verification_admin_bp
    from app.payments.routes import payments_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(auction_bp, url_prefix='/auction')
    app.register_blueprint(main_bp, url_prefix='/')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(assistant_bp)
    app.register_blueprint(verification_bp)
    app.register_blueprint(verification_admin_bp)
    app.register_blueprint(payments_bp)

    register_error_handlers(app)

    return app
