from auction7.app import create_app

app = create_app()

if __name__ == "__main__":
    print("Testing app creation...")
    print("App created successfully!")
    print("Configuration loaded:")
    print(f"Database URI: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not set')}")
    print(f"Stripe keys: {'Set' if app.config.get('STRIPE_SECRET_KEY') else 'Not set'}")
    print(f"Upload folder: {app.config.get('UPLOAD_FOLDER', 'Not set')}")