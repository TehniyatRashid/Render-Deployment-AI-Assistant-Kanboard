"""
Main Flask Application for AI Project Estimator
Production-ready for Render.com
"""

import os
import logging
import time
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

# ========== CONFIGURATION ==========
def create_app():
    app = Flask(__name__, 
                static_folder='static',
                template_folder='templates')
    
    # Database Configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL', 
        'sqlite:///keycodes.db'  # Default to SQLite for local development
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Other Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24))
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
    
    # ========== INITIALIZE EXTENSIONS ==========
    # Initialize CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Initialize Database
    from models import db
    db.init_app(app)  # ✅ CRITICAL: Connect db to app
    
    # Production logging
    if os.environ.get('FLASK_ENV') == 'production':
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        logging.basicConfig(level=logging.DEBUG)
    
    logger = logging.getLogger(__name__)
    logger.info("🚀 Starting Keycodes AI Assistant...")
    
    # Create database tables
    with app.app_context():
        try:
            db.create_all()
            logger.info("✅ Database tables created/verified")
        except Exception as e:
            logger.error(f"❌ Database initialization error: {e}")
    
    # ========== REGISTER YOUR BLUEPRINTS ==========
    try:
        # Register your existing blueprints
        from ai_task_creator import ai_task_blueprint
        from kanban_dashboard import kanban_blueprint
        from ticket_preview import ticket_preview_blueprint
        
        app.register_blueprint(ai_task_blueprint)
        app.register_blueprint(kanban_blueprint)
        app.register_blueprint(ticket_preview_blueprint)
        
        logger.info("✅ Blueprints registered successfully")
        
    except ImportError as e:
        logger.error(f"❌ Failed to import blueprints: {e}")
    
    # ========== SUPABASE CONNECTION CHECK ==========
    supabase_available = False
    try:
        from supabase import create_client
        
        supabase_url = os.environ.get('SUPABASE_URL')
        supabase_key = os.environ.get('SUPABASE_KEY')
        
        if supabase_url and supabase_key:
            # Just test connection
            create_client(supabase_url, supabase_key)
            supabase_available = True
            logger.info("✅ Supabase connection available")
        else:
            logger.warning("⚠️ Supabase credentials not found in environment variables")
            
    except Exception as e:
        logger.warning(f"⚠️ Supabase connection check failed: {e}")
    
    # ========== HEALTH CHECK ==========
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint for Render"""
        return jsonify({
            "status": "healthy",
            "service": "keycodes-ai-assistant",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
            "environment": os.environ.get("FLASK_ENV", "development"),
            "supabase_connected": supabase_available,
            "database": app.config['SQLALCHEMY_DATABASE_URI']
        }), 200
    
    # ========== MAIN ROUTES ==========
    @app.route('/')
    def index():
        """Serve main dashboard"""
        return render_template('index.html')
    
    @app.route('/dashboard')
    def dashboard():
        """Serve Kanban dashboard"""
        return render_template('kanban_dashboard.html')
    
    @app.route('/preview')
    def preview():
        """Serve ticket preview"""
        return render_template('ticket_preview.html')
    
    # ========== DATABASE TEST ENDPOINT ==========
    @app.route('/api/test-db', methods=['GET'])
    def test_database():
        """Test database connection"""
        from models import KanbanTicket, db
        try:
            # Test query
            ticket_count = KanbanTicket.query.count()
            
            # Test insertion
            test_ticket = KanbanTicket(
                ticket_id='test-db-connection',
                title='Database Test Ticket',
                description='Testing database connectivity',
                status='test'
            )
            
            db.session.add(test_ticket)
            db.session.commit()
            
            # Clean up
            db.session.delete(test_ticket)
            db.session.commit()
            
            return jsonify({
                "success": True,
                "message": "Database connection successful!",
                "ticket_count": ticket_count,
                "database_uri": app.config['SQLALCHEMY_DATABASE_URI']
            })
            
        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e),
                "database_uri": app.config['SQLALCHEMY_DATABASE_URI']
            }), 500
    
    @app.route('/api/info', methods=['GET'])
    def api_info():
        """API information endpoint"""
        return jsonify({
            "name": "Keycodes AI Assistant",
            "version": "1.0.0",
            "database": app.config['SQLALCHEMY_DATABASE_URI'].split('///')[-1] if '///' in app.config['SQLALCHEMY_DATABASE_URI'] else app.config['SQLALCHEMY_DATABASE_URI'],
            "storage": "supabase" if supabase_available else "sqlite",
            "endpoints_available": [
                "GET /api/test-db",
                "POST /api/estimate",
                "POST /api/create-ticket", 
                "GET /api/tickets",
                "GET /api/kanban",
                "GET /health"
            ]
        })
    
    # ========== SUPPORTING ENDPOINTS ==========
    @app.route('/api/tickets', methods=['GET'])
    def get_tickets():
        """Get all tickets"""
        try:
            from models import KanbanTicket
            tickets = KanbanTicket.query.all()
            return jsonify({
                "success": True,
                "tickets": [ticket.to_dict() for ticket in tickets],
                "count": len(tickets)
            })
        except Exception as e:
            logger.error(f"❌ Get tickets error: {str(e)}")
            return jsonify({
                "success": False,
                "error": "Database error: " + str(e)
            }), 500
    
    # ========== STATIC FILES ==========
    @app.route('/static/<path:filename>')
    def serve_static(filename):
        """Serve static files"""
        return send_from_directory('static', filename)
    
    # ========== ERROR HANDLERS ==========
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Endpoint not found"}), 404
    
    @app.errorhandler(429)
    def rate_limit_error(error):
        return jsonify({
            "error": "Rate limit exceeded",
            "message": "Too many requests. Please wait 60 seconds."
        }), 429
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"500 error: {str(error)}")
        return jsonify({
            "error": "Internal server error",
            "message": "Something went wrong on our end"
        }), 500
    
    logger.info("✅ App initialized successfully")
    return app

# ========== APPLICATION FACTORY ==========
app = create_app()

# ========== START APPLICATION ==========
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") != "production"
    
    logging.info(f"🚀 Starting server on port {port} (debug={debug})")
    app.run(host='0.0.0.0', port=port, debug=debug)