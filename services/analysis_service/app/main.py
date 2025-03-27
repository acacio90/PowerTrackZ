from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "analysis_service",
        "port": int(os.environ.get('PORT', 5002))
    })

@app.route('/analyze', methods=['GET'])
def analyze():
    # Mockup de análise
    results = [
        {"ponto_a": "Ap1", "ponto_b": "Ap2", "problema": "Conflito de Canal", "solucao": "Mudar para Canal 6"},
        {"ponto_a": "Ap3", "ponto_b": "Ap4", "problema": "Interferência de Frequência", "solucao": "Mudar para 5GHz"}
    ]
    return jsonify(results)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5002))
    app.run(host='0.0.0.0', port=port, debug=True)