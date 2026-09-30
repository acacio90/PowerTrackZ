import logging
import os
from datetime import datetime

from flask import Flask, Response, jsonify, request
from flask_cors import CORS

from access_point_generator import generate_access_point_infrastructure
from access_point_import import import_access_points, upsert_access_point, validate_access_point_payload
from controllers import AccessPointController, create_tables
from models import AccessPoint, ScalabilityRun, db
from scalability import (
    ScalabilityConflict,
    ScalabilityRunner,
    mark_interrupted_runs,
    run_to_csv,
    run_to_dict,
)
from zabbix_integration import (
    get_zabbix_config,
    get_zabbix_groups,
    get_zabbix_hosts,
    save_zabbix_config,
    test_zabbix_connection,
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["ACCESS_POINT_DATABASE_URI"]
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

with app.app_context():
    create_tables()
    mark_interrupted_runs()

scalability_runner = ScalabilityRunner(app)


@app.route("/health")
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "access_point_service",
        "port": int(os.environ.get("PORT", 5004)),
    })


@app.route("/hosts", methods=["GET"])
def list_hosts():
    try:
        controller = AccessPointController()
        return controller.list_hosts()
    except Exception as e:
        logger.error(f"Erro ao listar hosts: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/hosts/<host_id>", methods=["GET"])
def get_host_details(host_id):
    try:
        controller = AccessPointController()
        return controller.get_host_details(host_id)
    except Exception as e:
        logger.error(f"Erro ao buscar detalhes do host: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/sync/zabbix", methods=["POST"])
def sync_zabbix():
    try:
        controller = AccessPointController()
        return controller.sync_zabbix_data()
    except Exception as e:
        logger.error(f"Erro na sincronizacao: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/zabbix/test-connection", methods=["POST"])
def zabbix_test_connection():
    return test_zabbix_connection()


@app.route("/zabbix/save-config", methods=["POST"])
def zabbix_save_config():
    return save_zabbix_config()


@app.route("/zabbix/config", methods=["GET"])
def zabbix_config():
    return get_zabbix_config()


@app.route("/zabbix/groups", methods=["GET"])
def zabbix_groups():
    return get_zabbix_groups()


@app.route("/zabbix/hosts", methods=["GET"])
def zabbix_hosts():
    return get_zabbix_hosts()


@app.route("/access_points", methods=["POST"])
def create_access_point():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Dados obrigatorios nao enviados"}), 400

        errors = validate_access_point_payload(data)
        if errors:
            return jsonify({"error": "Dados invalidos", "details": errors}), 400

        upsert_access_point(data)
        db.session.commit()
        return jsonify({"success": True, "message": "Ponto de acesso salvo/atualizado com sucesso!"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route("/access_points/import", methods=["POST"])
def bulk_import_access_points():
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"error": "Dados obrigatorios nao enviados"}), 400

        summary = import_access_points(data)
        return jsonify({
            "success": True,
            "message": "Importacao concluida",
            "summary": summary,
        }), 200
    except ValueError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route("/access_points/generate", methods=["POST"])
def generate_access_points():
    try:
        data = request.get_json() or {}
        node_count = int(data.get("node_count", 0))
        # "clique_factor" e o nome anterior de "min_degree", aceito por compatibilidade.
        min_degree = int(data.get("min_degree", data.get("clique_factor", 0)))
        payload = generate_access_point_infrastructure(node_count, min_degree, data.get("seed"))
        return jsonify({"success": True, "payload": payload}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/access_points", methods=["GET"])
def get_access_points():
    try:
        aps = AccessPoint.query.all()
        return jsonify([{
            "id": ap.id,
            "name": ap.name,
            "channel": ap.channel,
            "frequency": ap.frequency,
            "bandwidth": ap.bandwidth,
            "latitude": ap.latitude,
            "longitude": ap.longitude,
            "last_update": ap.last_update.isoformat() if ap.last_update else None,
        } for ap in aps])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/access_points/<id>", methods=["GET"])
def get_access_point(id):
    try:
        ap = db.session.get(AccessPoint, id)
        if not ap:
            return jsonify({"error": "Ponto de acesso nao encontrado"}), 404
        return jsonify(ap.to_dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/access_points/<id>", methods=["PUT"])
def update_access_point(id):
    try:
        data = request.get_json()
        ap = AccessPoint.query.get(id)
        if not ap:
            return jsonify({"error": "Ponto de acesso nao encontrado"}), 404

        ap.name = data.get("name", ap.name)
        ap.channel = data.get("channel", ap.channel)
        ap.frequency = data.get("frequency", ap.frequency)
        ap.bandwidth = data.get("bandwidth", ap.bandwidth)
        ap.latitude = data.get("latitude", ap.latitude)
        ap.longitude = data.get("longitude", ap.longitude)
        ap.last_update = datetime.utcnow()

        db.session.commit()
        return jsonify({"success": True, "message": "Ponto de acesso atualizado com sucesso!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route("/access_points/<id>", methods=["DELETE"])
def delete_access_point(id):
    try:
        ap = AccessPoint.query.get(id)
        if not ap:
            return jsonify({"error": "Ponto de acesso nao encontrado"}), 404

        db.session.delete(ap)
        db.session.commit()
        return jsonify({"success": True, "message": "Ponto de acesso removido com sucesso!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route("/experiments/scalability", methods=["GET"])
def list_scalability_runs():
    runs = ScalabilityRun.query.order_by(ScalabilityRun.id.desc()).all()
    return jsonify({"success": True, "runs": [run_to_dict(run, include_points=False) for run in runs]})


@app.route("/experiments/scalability", methods=["POST"])
def start_scalability_run():
    try:
        run = scalability_runner.start(request.get_json(silent=True) or {})
        return jsonify({"success": True, "run": run_to_dict(run)}), 202
    except ValueError as error:
        return jsonify({"success": False, "error": str(error)}), 400
    except ScalabilityConflict as error:
        return jsonify({"success": False, "error": str(error)}), 409
    except Exception as error:
        logger.exception("Falha ao iniciar o teste de escalabilidade")
        return jsonify({"success": False, "error": str(error)}), 500


@app.route("/experiments/scalability/<int:run_id>", methods=["GET"])
def get_scalability_run(run_id):
    run = db.session.get(ScalabilityRun, run_id)
    if not run:
        return jsonify({"success": False, "error": "Execucao nao encontrada"}), 404
    return jsonify({"success": True, "run": run_to_dict(run)})


@app.route("/experiments/scalability/<int:run_id>/cancel", methods=["POST"])
def cancel_scalability_run(run_id):
    if not scalability_runner.cancel(run_id):
        return jsonify({"success": False, "error": "Execucao nao esta em andamento"}), 409
    return jsonify({"success": True, "message": "Cancelamento solicitado"})


@app.route("/experiments/scalability/<int:run_id>", methods=["DELETE"])
def delete_scalability_run(run_id):
    run = db.session.get(ScalabilityRun, run_id)
    if not run:
        return jsonify({"success": False, "error": "Execucao nao encontrada"}), 404
    if scalability_runner.is_active(run_id):
        return jsonify({"success": False, "error": "Cancele a execucao antes de exclui-la"}), 409
    db.session.delete(run)
    db.session.commit()
    return jsonify({"success": True})


@app.route("/experiments/scalability/<int:run_id>/export", methods=["GET"])
def export_scalability_run(run_id):
    run = db.session.get(ScalabilityRun, run_id)
    if not run:
        return jsonify({"success": False, "error": "Execucao nao encontrada"}), 404
    export_format = request.args.get("format", "json")
    filename = f"powertrackz-escalabilidade-{run_id}"
    if export_format == "csv":
        return Response(
            run_to_csv(run),
            mimetype="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}.csv"'},
        )
    if export_format == "json":
        response = jsonify(run_to_dict(run))
        response.headers["Content-Disposition"] = f'attachment; filename="{filename}.json"'
        return response
    return jsonify({"success": False, "error": "format deve ser csv ou json"}), 400


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5004))
    host = os.environ.get("HOST", "0.0.0.0")
    debug = os.environ.get("FLASK_ENV", "development") == "development"
    app.run(host=host, port=port, debug=debug)
