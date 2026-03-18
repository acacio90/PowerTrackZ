from flask import Flask
from flask_cors import CORS
import logging
import os

from routes import routes


logging.basicConfig(level=logging.INFO)


def create_app():
    app = Flask(__name__)
    CORS(app)
    app.register_blueprint(routes)
    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))
    app.run(host="0.0.0.0", port=port, debug=True)
