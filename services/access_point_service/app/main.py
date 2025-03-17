from flask import Flask
from models import db  # Ajuste na importação
import controllers  # Importar o controlador

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///access_points.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

@app.before_first_request
def create_tables():
    controllers.create_tables()

@app.route('/register', methods=['POST'])
def register():
    return controllers.register()

@app.route('/access_points', methods=['GET'])
def get_access_points():
    return controllers.get_access_points()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)