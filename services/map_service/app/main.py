from flask import Flask
import controllers

app = Flask(__name__)

@app.route('/map', methods=['GET'])
def get_map():
    return controllers.get_map()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)