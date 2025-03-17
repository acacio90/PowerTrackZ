from flask import Flask, jsonify, request
import requests

app = Flask(__name__)

@app.route('/access_points', methods=['GET'])
def get_access_points():
    response = requests.get('http://access_point_service:5000/access_points', json=request.get_json())
    return jsonify(response.json()), response.status_code

@app.route('/register', methods=['POST'])
def register():
    response = requests.post('http://access_point_service:5000/register', json=request.get_json())
    return jsonify(response.json()), response.status_code

@app.route('/map', methods=['GET'])
def get_map():
    try:
        response = requests.get('http://map_service:5001/map')
        if response.status_code == 200:
            return response.content, response.status_code, {'Content-Type': 'text/html'}
        else:
            return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"message": "Error connecting to map service", "error": str(e)}), 500

@app.route('/analyze', methods=['GET'])
def analyze():
    response = requests.get('http://analysis_service:5002/analyze')
    return jsonify(response.json()), response.status_code

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)