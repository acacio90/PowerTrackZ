from datetime import datetime

from models import AccessPoint, db


ALLOWED_FIELDS = {
    "id",
    "name",
    "channel",
    "frequency",
    "bandwidth",
    "latitude",
    "longitude",
}
OPTIONAL_IGNORED_FIELDS = {"last_update"}
REQUIRED_FIELDS = {"id", "name"}


def _is_blank(value):
    return value is None or (isinstance(value, str) and not value.strip())


def _validate_coordinates(payload):
    errors = []

    for field in ("latitude", "longitude"):
        value = payload.get(field)
        if value is None:
            continue

        try:
            payload[field] = float(value)
        except (TypeError, ValueError):
            errors.append(f"campo '{field}' deve ser numérico")

    return errors


def validate_access_point_payload(payload):
    if not isinstance(payload, dict):
        return ["item deve ser um objeto JSON"]

    errors = []
    unexpected_fields = sorted(set(payload.keys()) - ALLOWED_FIELDS - OPTIONAL_IGNORED_FIELDS)
    if unexpected_fields:
        errors.append(
            "campos não suportados: " + ", ".join(unexpected_fields)
        )

    for field in REQUIRED_FIELDS:
        if _is_blank(payload.get(field)):
            errors.append(f"campo obrigatório '{field}' não informado")

    errors.extend(_validate_coordinates(payload))

    return errors


def upsert_access_point(payload):
    ap = AccessPoint.query.get(payload["id"])
    created = ap is None

    if created:
        ap = AccessPoint(id=payload["id"])
        db.session.add(ap)

    ap.name = payload["name"]
    ap.channel = payload.get("channel")
    ap.frequency = payload.get("frequency")
    ap.bandwidth = payload.get("bandwidth")
    ap.latitude = payload.get("latitude")
    ap.longitude = payload.get("longitude")
    ap.last_update = datetime.utcnow()

    return ap, created


def import_access_points(payload):
    if not isinstance(payload, list):
        raise ValueError("o corpo da requisição deve ser uma lista JSON de pontos de acesso")

    summary = {
        "processed": len(payload),
        "created": 0,
        "updated": 0,
        "rejected": 0,
        "errors": [],
    }
    seen_ids = set()

    for index, item in enumerate(payload):
        errors = validate_access_point_payload(item)

        if isinstance(item, dict) and item.get("id") in seen_ids:
            errors.append(f"id duplicado no arquivo: '{item['id']}'")

        if errors:
            summary["rejected"] += 1
            summary["errors"].append({
                "index": index,
                "id": item.get("id") if isinstance(item, dict) else None,
                "reasons": errors,
            })
            continue

        seen_ids.add(item["id"])
        _, created = upsert_access_point(item)
        if created:
            summary["created"] += 1
        else:
            summary["updated"] += 1

    db.session.commit()
    return summary
