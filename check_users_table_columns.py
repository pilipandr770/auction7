from app import create_app, db
from app.models.user import User

app = create_app()
with app.app_context():
    insp = db.inspect(db.engine)
    columns = insp.get_columns('users')
    print('users table columns:')
    for col in columns:
        print(col['name'])
