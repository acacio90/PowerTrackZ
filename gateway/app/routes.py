from flask import Blueprint, jsonify, request, render_template, redirect, url_for
import requests

routes = Blueprint('routes', __name__)

@routes.route('/')
def index():
    return render_template('pages/index.html')

@routes.route('/access_points', methods=['GET'])
def get_access_points():
    try:
        response = requests.get('http://access_point_service:5000/access_points')
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"message": "Error connecting to access point service", "error": str(e)}), 500

@routes.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            data = {
                "description": request.form['description'],
                "latitude": request.form['latitude'],
                "longitude": request.form['longitude'],
                "frequency": request.form['frequency'],
                "bandwidth": request.form['bandwidth'],
                "channel": request.form['channel']
            }
            response = requests.post('http://access_point_service:5000/register', json=data)
            if response.status_code == 201:
                return redirect(url_for('routes.register'))
            else:
                return jsonify(response.json()), response.status_code
        except requests.exceptions.RequestException as e:
            return jsonify({"message": "Error connecting to access point service", "error": str(e)}), 500
    try:
        response = requests.get('http://access_point_service:5000/access_points')
        access_points = response.json()
    except requests.exceptions.RequestException as e:
        access_points = []

    try:
        map_response = requests.get('http://map_service:5001/map')
        if map_response.status_code == 200:
            map_html = map_response.text
        else:
            map_html = "<p>Error loading map</p>"
    except requests.exceptions.RequestException as e:
        map_html = "<p>Error connecting to map service</p>"

    return render_template('pages/register.html', access_points=access_points, map_html=map_html)

@routes.route('/map', methods=['GET'])
def get_map():
    try:
        response = requests.get('http://map_service:5001/map')
        if response.status_code == 200:
            return response.content, response.status_code, {'Content-Type': 'text/html'}
        else:
            return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"message": "Error connecting to map service", "error": str(e)}), 500

@routes.route('/analyze', methods=['GET'])
def analyze():
    try:
        response = requests.get('http://analysis_service:5002/analyze')
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"message": "Error connecting to analysis service", "error": str(e)}), 500