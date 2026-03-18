from flask import Flask
import logging

from routes import routes


logging.basicConfig(level=logging.INFO)


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'frontend_secret_key'
    app.register_blueprint(routes)
    return app


app = create_app()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)
