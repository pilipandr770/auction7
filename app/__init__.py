from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

# Ініціалізація бази даних
app = None
db = SQLAlchemy()
migrate = Migrate()

login_manager = LoginManager()

def create_app():
    global app
    app = Flask(__name__)
    
    # Конфігурація бази даних
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///auction.db'  # Змінити на реальну базу за потреби
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'your_secret_key_here'
    
    # Підключення бази даних
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Налаштування сесій
    app.config['SESSION_PERMANENT'] = False
    app.config['SESSION_TYPE'] = 'filesystem'

    # Завантаження користувача
    from app.models.user import User  # Імпортуємо модель User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Реєстрація моделей
    from app.models.auction import Auction  # Додаємо Auction для реєстрації
    from app.models.user import User

    # Імпортуємо та реєструємо маршрути
    from app.routes.auth_routes import auth_bp
    from app.routes.user_routes import user_bp
    from app.routes.auction_routes import auction_bp
    from app.routes.main_routes import main_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(auction_bp, url_prefix='/auction')
    app.register_blueprint(main_bp, url_prefix='/')

    return app

# Імпортуємо db для використання в моделях
from app import db
