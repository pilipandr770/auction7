from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

# Ініціалізація розширень
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)

    # Конфігурація
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///auction.db'  # Змінити для продакшну
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'your_secret_key_here'
    app.config['SESSION_PERMANENT'] = False
    app.config['SESSION_TYPE'] = 'filesystem'

    # Ініціалізація розширень
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Завантаження користувача
    from app.models.user import User  # Імпорт моделі User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Реєстрація моделей (за потреби)
    from app.models.auction import Auction
    from app.models.auction_participant import AuctionParticipant
    from app.models.payment import Payment

    # Реєстрація маршрутів
    from app.routes.auth_routes import auth_bp
    from app.routes.user_routes import user_bp
    from app.routes.auction_routes import auction_bp
    from app.routes.main_routes import main_bp
    from app.routes.admin_routes import admin_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(auction_bp, url_prefix='/auction')
    app.register_blueprint(main_bp, url_prefix='/')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    return app
