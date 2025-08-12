from flask import Flask, render_template, request, jsonify, redirect, url_for
import requests
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = 'frontend_secret_key'

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# URLs dos serviços (via gateway)
GATEWAY_URL = "http://gateway:80"

def make_api_request(endpoint, method='GET', data=None):
    """Faz requisição para a API via gateway"""
    try:
        url = f"{GATEWAY_URL}/api{endpoint}"
        if method == 'GET':
            response = requests.get(url)
        elif method == 'POST':
            response = requests.post(url, json=data)
        elif method == 'PUT':
            response = requests.put(url, json=data)
        elif method == 'DELETE':
            response = requests.delete(url)
        
        return response.json(), response.status_code
    except Exception as e:
        logger.error(f"Erro na requisição para {endpoint}: {str(e)}")
        return {"error": str(e)}, 500

@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "frontend_service",
        "port": 3000
    })

@app.route('/')
def index():
    return render_template('pages/index.html')

@app.route('/hosts')
def hosts():
    try:
        hosts_data, status_code = make_api_request('/zabbix/hosts')
        if status_code == 200:
            hosts = hosts_data.get("data", []) if hosts_data.get("success") else []
            return render_template('pages/hosts.html', hosts=hosts)
        return render_template('pages/hosts.html', hosts=[], error=hosts_data)
    except Exception as e:
        return render_template('pages/hosts.html', hosts=[], error={"error": str(e)})

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            data = {
                "id": request.form.get('id', request.form['description']),
                "name": request.form['description'],
                "channel": request.form['channel'],
                "frequency": request.form['frequency'],
                "bandwidth": request.form['bandwidth'],
                "latitude": request.form['latitude'],
                "longitude": request.form['longitude']
            }
            
            result, status_code = make_api_request('/access_points', 'POST', data)
            
            if status_code == 201:
                return redirect(url_for('register'))
            else:
                return render_template('pages/register.html', error=result)
        except Exception as e:
            return render_template('pages/register.html', error={"error": str(e)})

    # GET request - carrega dados
    try:
        points_data, _ = make_api_request('/access_points')
        points = points_data if isinstance(points_data, list) else []
    except Exception:
        points = []

    try:
        map_data, _ = make_api_request('/map')
        map_html = map_data if isinstance(map_data, str) else "<p>Error loading map</p>"
    except Exception:
        map_html = "<p>Error loading map</p>"

    return render_template('pages/register.html', points=points, map_html=map_html)

@app.route('/analysis')
def analysis():
    try:
        points_data, _ = make_api_request('/access_points')
        points = points_data if isinstance(points_data, list) else []
    except Exception:
        points = []
    return render_template('pages/analysis.html', points=points)

@app.route('/settings')
def settings():
    return render_template('pages/settings.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True) 