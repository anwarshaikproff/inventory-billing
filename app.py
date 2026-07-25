import os
from flask import Flask
from database.db import init_db, close_db
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.products import products_bp
from routes.pos import pos_bp
from routes.scanner import scanner_bp
from routes.offers import offers_bp
from routes.settings import settings_bp
from routes.customers import customers_bp
from routes.suppliers import suppliers_bp
from routes.inventory import inventory_bp
from routes.db_management import db_management_bp
from routes.api_routes import api_bp

def create_app():
    """
    Application Factory to configure Flask app, 
    initialize database schemas, and load modular controllers.
    """
    app = Flask(__name__)
    
    # Session configurations
    app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'techmart_secret_key_987654321')

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(pos_bp)
    app.register_blueprint(scanner_bp)
    app.register_blueprint(offers_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(suppliers_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(db_management_bp)
    app.register_blueprint(api_bp)

    @app.context_processor
    def inject_db_status():
        from database.db import get_db_status
        return dict(sidebar_db_status=get_db_status())

    # Teardown connection close handlers
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        close_db(exception)

    # Initialize SQLite database schemas & seed defaults on startup
    with app.app_context():
        success = init_db()
        if not success:
            print("Database initialization encountered errors.")
            
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting SKML Mobiles POS & Inventory Server on http://127.0.0.1:{port}")
    # Bind to localhost port for standard local server dev access
    app.run(debug=True, host='127.0.0.1', port=port)
