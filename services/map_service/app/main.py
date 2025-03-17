from flask import Flask, jsonify
from models import db, AccessPoint # Ajuste na importação
import controllers  # Importar o controlador

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///access_points.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

@app.before_first_request
def create_tables():
    controllers.create_tables()

@app.route('/map', methods=['GET'])
def get_map():
    return controllers.get_map()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)