import os
from flask import Flask, redirect, url_for, flash
from database.db import init_db, close_db, load_env
from routes.billing import billing_bp

# Ensure environment is explicitly loaded before starting application factory
load_env()

def create_app():
    """
    Application Factory to configure Flask app, 
    initialize database schemas, and load unified billing controllers.
    """
    app = Flask(__name__)
    
    # Session configurations
    app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'techmart_secret_key_987654321')

    # Register core unified billing blueprint
    app.register_blueprint(billing_bp)

    @app.context_processor
    def inject_db_status():
        from database.db import get_db_status
        return dict(sidebar_db_status=get_db_status())

    # Catch-all handler for legacy URLs (/products, /pos, /login, etc.)
    @app.errorhandler(404)
    def handle_not_found(error):
        """Redirects any legacy or unmapped URLs directly to the modern billing desk."""
        return redirect(url_for('billing.index'))

    @app.errorhandler(500)
    def handle_server_error(error):
        """Prevents ugly application crash pages by safely routing back to main UI."""
        return redirect(url_for('billing.index'))

    # Teardown connection close handlers
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        close_db(exception)

    # Initialize PostgreSQL database schema & drop legacy tables on startup
    with app.app_context():
        success = init_db()
        if not success:
            print("Database initialization encountered errors.")
            
    return app

# Expose global app instance for WSGI cloud runners (Gunicorn / Render / Vercel)
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print(f"Starting SKML Mobiles Unified Billing Server on port {port}")
    # Bind to 0.0.0.0 so containerized cloud runners (Render/Docker) can accept incoming external HTTP traffic
    app.run(debug=True, host='0.0.0.0', port=port)

