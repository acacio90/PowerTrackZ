from flask import Flask, jsonify, render_template
from flask_cors import CORS
import logging
from .config import Config
from .routes import routes

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # CORS
    CORS(app)
    
    # Logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Rotas
    app.register_blueprint(routes)
    
    # Rota principal
    @app.route('/')
    def index():
        return render_template('pages/index.html')
    
    # Healthcheck
    @app.route('/health')
    def health_check():
        return jsonify({
            "status": "healthy",
            "service": "gateway",
            "port": 80
        })
    
    return app
