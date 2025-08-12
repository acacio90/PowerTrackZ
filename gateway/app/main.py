from flask import Flask
from .routes import routes
from .config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Registra as rotas
    app.register_blueprint(routes)
    
    return app

app = create_app()

if __name__ == '__main__':
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)