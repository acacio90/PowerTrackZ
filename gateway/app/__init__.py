from flask import Flask
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
    
        app.register_blueprint(routes)
    
    return app
