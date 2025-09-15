from flask import Flask, session, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ініціалізація розширень
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

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

    # Конфігурація з змінних середовища
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///auction.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_secret_key_here_change_this')
    app.config['SESSION_PERMANENT'] = os.getenv('SESSION_PERMANENT', 'False').lower() == 'true'
    app.config['SESSION_TYPE'] = os.getenv('SESSION_TYPE', 'filesystem')
    
    # Stripe Configuration
    app.config['STRIPE_PUBLISHABLE_KEY'] = os.getenv('STRIPE_PUBLISHABLE_KEY')
    app.config['STRIPE_SECRET_KEY'] = os.getenv('STRIPE_SECRET_KEY')
    app.config['STRIPE_WEBHOOK_SECRET'] = os.getenv('STRIPE_WEBHOOK_SECRET')
    
    # Upload Configuration
    app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'auction7/app/static/images/uploads')
    app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 16777216))  # 16MB
    app.config['ALLOWED_EXTENSIONS'] = os.getenv('ALLOWED_EXTENSIONS', 'jpg,jpeg,png,gif,webp').split(',')

    # Ініціалізація розширень
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Завантаження користувача
    from auction7.app.models.user import User  # Імпорт моделі User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Реєстрація моделей та роутів
    from auction7.app.models.user import User
    from auction7.app.models.auction import Auction
    from auction7.app.models.auction_participant import AuctionParticipant
    from auction7.app.models.payment import Payment
    
    try:
        from auction7.app.routes.auth_routes import auth_bp
        app.register_blueprint(auth_bp, url_prefix='/auth')
    except ImportError as e:
        print(f"Warning: Could not import auth_routes: {e}")
        
    try:
        from auction7.app.routes.user_routes import user_bp
        app.register_blueprint(user_bp, url_prefix='/user')
    except ImportError as e:
        print(f"Warning: Could not import user_routes: {e}")
        
    try:
        from auction7.app.routes.auction_routes import auction_bp
        app.register_blueprint(auction_bp, url_prefix='/auction')
    except ImportError as e:
        print(f"Warning: Could not import auction_routes: {e}")
        
    try:
        from auction7.app.routes.main_routes import main_bp
        app.register_blueprint(main_bp, url_prefix='/')
    except ImportError as e:
        print(f"Warning: Could not import main_routes: {e}")
        
    try:
        from auction7.app.routes.admin_routes import admin_bp
        app.register_blueprint(admin_bp, url_prefix='/admin')
    except ImportError as e:
        print(f"Warning: Could not import admin_routes: {e}")
        
    try:
        from auction7.app.routes.payment_routes import payment_bp
        app.register_blueprint(payment_bp, url_prefix='/payment')
    except ImportError as e:
        print(f"Warning: Could not import payment_routes: {e}")
        
    # Optional routes
    try:
        from assistans.routes import assistant_bp
        app.register_blueprint(assistant_bp)
    except ImportError:
        print("Warning: Assistant routes not available")
        
    try:
        from auction7.app.verification.routes import verification_bp
        from auction7.app.verification.admin_routes import verification_admin_bp
        app.register_blueprint(verification_bp, url_prefix='/verification')
        app.register_blueprint(verification_admin_bp, url_prefix='/admin/verification')
    except ImportError:
        print("Warning: Verification routes not available")

    # Реєстрація обробників помилок
    register_error_handlers(app)

    return app
