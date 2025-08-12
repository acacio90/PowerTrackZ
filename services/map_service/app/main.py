from flask import Flask, jsonify
from app.controllers import get_map
import os

app = Flask(__name__)

@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "map_service",
        "port": int(os.environ.get('PORT', 5001))
    })

@app.route('/map', methods=['GET'])
def map():
    return get_map()

@app.route('/points', methods=['GET'])
def points():
    return get_map_points()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)