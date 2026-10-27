"""Strict evidence gate around the CAD exporter. Metadata checks are not certification."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
try:
    from . import cad_pipeline as engine, assurance
except ImportError:
    import cad_pipeline as engine
    import assurance

FIELDS = {
    "LINE": ("start", "end"),
    "LWPOLYLINE": ("points", "closed"),
    "CIRCLE": ("center", "radius"),
    "ARC": ("center", "radius", "start_angle", "end_angle"),
    "ELLIPSE": ("center", "major_axis", "ratio", "start_param", "end_param"),
    "SPLINE": ("control_points", "degree", "knots"),
    "TEXT": ("text", "insert", "height", "rotation"),
    "MTEXT": ("text", "insert", "height", "width", "rotation"),
    "HATCH": ("boundary", "pattern", "pattern_scale", "pattern_angle"),
    "DIMENSION": ("p1", "p2", "base", "angle", "text_height", "arrow_size", "decimals"),
}
ANNOTATIONS = {"TEXT", "MTEXT", "DIMENSION"}
BASIS = {"explicit_dimensions", "derived_constraints", "authoritative_vectors", "graphical_annotation"}
KINDS = {"dimension", "datum", "constraint", "authoritative_vector", "graphical_annotation"}


def fail(message):
    raise ValueError("BLOQUEADO: " + message)


def positive(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def index_unique(rows, label):
    if not isinstance(rows, list) or not rows:
        fail(label + ": lista vacia o ausente")
    result = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"].strip():
            fail(label + ": falta ID")
        if row["id"] in result:
            fail(label + ": ID duplicado " + row["id"])
        result[row["id"]] = row
    return result


def check(model_path):
    import ezdxf

    model_path = Path(model_path).resolve()
    model = load(model_path)
    engine.finite_tree(model)
    if model.get("units") not in {"mm", "cm", "m", "in"}:
        fail("unidad no definida")
    eng = model.get("engineering", {})
    if not eng.get("scope") or not eng.get("tolerance_basis") or not positive(eng.get("comparison_tolerance")):
        fail("faltan alcance o criterio de comparacion positivo con procedencia")
    if model.get("issues") != []:
        fail("resolver y conservar el registro de incidencias antes de exportar")
    coverage = model.get("coverage", {})
    if coverage.get("review") != "complete" or coverage.get("omitted") != []:
        fail("cobertura del alcance incompleta")
    sources = index_unique(eng.get("sources"), "fuentes")
    page_counts = {}
    for sid, source in sources.items():
        if not source.get("path"):
            fail(sid + ": falta ruta")
        src = (model_path.parent / source["path"]).resolve()
        if not src.is_file():
            fail(sid + ": original inaccesible")
        digest = hashlib.sha256(src.read_bytes()).hexdigest()
        if source.get("sha256") != digest:
            fail(sid + ": hash no coincide")
        if src.suffix.lower() == ".pdf":
            import pymupdf
            with pymupdf.open(src) as pdf:
                page_counts[sid] = len(pdf)
        else:
            from PIL import Image
            with Image.open(src) as image:
                page_counts[sid] = getattr(image, "n_frames", 1)
    evidence = index_unique(eng.get("evidence"), "evidencia")
    for eid, item in evidence.items():
        sid, page = item.get("source_id"), item.get("page")
        if sid not in sources or not isinstance(page, int) or isinstance(page, bool) or not 1 <= page <= page_counts[sid]:
            fail(eid + ": fuente o pagina invalida")
        if item.get("kind") not in KINDS or not item.get("locator") or not item.get("statement"):
            fail(eid + ": evidencia incompleta")
        if item["kind"] == "dimension":
            value = item.get("normalized_value")
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                fail(eid + ": valor nominal ausente")
            if item.get("normalized_units") != model["units"]:
                fail(eid + ": convertir unidades explicitamente")
    cal = model.get("calibration", {})
    cal_ids = cal.get("evidence_ids", [])
    if cal.get("status") != "referenced" or not cal.get("references") or not cal_ids:
        fail("referencia dimensional de calibracion ausente")
    if any(eid not in evidence or evidence[eid]["kind"] not in {"dimension", "authoritative_vector"} for eid in cal_ids):
        fail("calibracion sin evidencia dimensional/vectorial")
    anchors = model.get("registration", {}).get("anchors", [])
    if len(anchors) < 3:
        fail("usar al menos tres anclajes no colineales")
    for key in ("cad", "pixel"):
        points = np.array([anchor[key] for anchor in anchors], dtype=float)
        if points.shape != (len(anchors), 2) or np.linalg.matrix_rank(np.column_stack([points, np.ones(len(points))])) != 3:
            fail("anclajes colineales o degenerados")
    engine.registration(model)
    uncertainty = assurance.validate(model, model_path.parent)
    entities = index_unique(model.get("entities"), "entidades")
    signatures = set()
    doc = ezdxf.new("R2013", setup=True)
    temporary = {}
    for eid, item in entities.items():
        if item.get("type") not in FIELDS:
            fail(eid + ": ampliar exportador para este tipo")
        if item.get("state") != "VERIFICADO" or not item.get("evidence") or not item.get("layer"):
            fail(eid + ": estado o procedencia no verificados")
        definition = item.get("definition", {})
        basis = definition.get("basis")
        if definition.get("fully_constrained") is not True or basis not in BASIS:
            fail(eid + ": geometria no completamente definida")
        required = {k for k in FIELDS[item["type"]] if k in item}
        if not required.issubset(set(definition.get("parameters", []))):
            fail(eid + ": parametros sin procedencia declarada")
        refs = definition.get("evidence_ids", [])
        if not refs or any(ref not in evidence for ref in refs):
            fail(eid + ": referencias inexistentes")
        kinds = {evidence[ref]["kind"] for ref in refs}
        if basis == "explicit_dimensions" and "dimension" not in kinds:
            fail(eid + ": faltan cotas explicitas")
        if basis == "derived_constraints" and (not definition.get("derivation") or not kinds.intersection({"dimension", "constraint"})):
            fail(eid + ": derivacion ausente")
        if basis == "authoritative_vectors" and "authoritative_vector" not in kinds:
            fail(eid + ": vector sin autoridad documentada")
        if basis == "graphical_annotation" and item["type"] not in ANNOTATIONS:
            fail(eid + ": dato grafico usado como geometria fisica")
        if item["type"] not in ANNOTATIONS:
            signature = json.dumps({k: item[k] for k in ("type", *FIELDS[item["type"]]) if k in item}, sort_keys=True)
            if signature in signatures:
                fail(eid + ": geometria duplicada")
            signatures.add(signature)
        temporary[eid] = engine.make_entity(doc.modelspace(), item, {"layer": "0", "color": 7})
    controls = index_unique(model.get("controls"), "controles")
    controlled, independent = set(), 0
    control_results = []
    for cid, item in controls.items():
        eid, ev_id = item.get("entity"), item.get("evidence_id")
        if eid not in entities or ev_id not in evidence or evidence[ev_id]["kind"] != "dimension":
            fail(cid + ": control sin entidad o cota fuente")
        if item.get("role") not in {"calibration", "independent"} or not item.get("evidence") or not item.get("tolerance_basis"):
            fail(cid + ": control incompleto")
        tolerance = item.get("tolerance")
        if not positive(tolerance) or tolerance > eng["comparison_tolerance"]:
            fail(cid + ": tolerancia ausente o mas permisiva que el criterio")
        if item.get("expected") != evidence[ev_id]["normalized_value"]:
            fail(cid + ": esperado distinto de la cota documentada")
        if item["role"] == "independent":
            if ev_id in cal_ids:
                fail(cid + ": control reutiliza calibracion")
            independent += 1
        actual = engine.measured_control(item, temporary[eid])
        if abs(actual - item["expected"]) > tolerance:
            fail(cid + ": dimension CAD incompatible con fuente")
        controlled.add(eid)
        control_results.append({"id": cid, "measured": actual, "expected": item["expected"]})
    if not independent:
        fail("falta al menos una cota independiente del ajuste")
    missing = {eid for eid, item in entities.items() if item["type"] not in ANNOTATIONS} - controlled
    if missing:
        fail("faltan controles numericos; ampliar medidor si procede: " + ", ".join(sorted(missing)))
    return {"status": "STRUCTURED_EVIDENCE_CHECKED_REVIEW_PENDING", "scope": eng["scope"],
            "entities": len(entities), "controls": control_results, "uncertainty": uncertainty,
            "note": "Comprobacion estructural y numerica; no certifica la interpretacion ni la exactitud fisica."}


def build(model_path, output):
    gate = check(model_path)
    if Path(output).exists():
        raise FileExistsError(output)
    try:
        report = engine.build(model_path, output)
    except Exception:
        if Path(output).is_dir():
            engine.dump(Path(output) / 'status.json', {'status': 'INCOMPLETE_DO_NOT_USE'})
        raise
    engine.dump(Path(output) / 'status.json', {'status': 'INCOMPLETE_DO_NOT_USE'})
    if report["audit_errors"] or report["audit_fixes"] or any(c["result"] != "PASS" for c in report["controls"]):
        engine.dump(Path(output) / 'status.json', {'status': 'INCOMPLETE_DO_NOT_USE'})
        fail("fallo al reabrir CAD; salida parcial no entregable")
    result = {**gate, "status": "DEFINED_REVIEW_PENDING", "export_reopened": True,
              "dxf_sha256": report["dxf_sha256"], "review": "PENDIENTE",
              "required": ["Revision semantica y de cobertura", "Revision visual con registro fijo",
                           "Comprobaciones especializadas del alcance"]}
    model = load(model_path)
    portable = assurance.portable_sources(model, Path(model_path).resolve().parent, output)
    engine.dump(Path(output) / "modelo-reproducible.json", portable)
    engine.dump(Path(output) / "engineering-check.json", result)
    engine.dump(Path(output) / 'status.json', {'status': 'DEFINED_REVIEW_PENDING'})
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check").add_argument("model")
    export = sub.add_parser("build")
    export.add_argument("model")
    export.add_argument("output")
    args = parser.parse_args()
    try:
        result = check(args.model) if args.command == "check" else build(args.model, args.output)
        print(json.dumps(result, ensure_ascii=False))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.exit(2, str(exc) + "\n")

