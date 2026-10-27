"""Synthetic engineering regression checks; no claim about real-source fidelity."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw
try:
    from .cad_pipeline import dump, inspect_source
    from .engineering_gate import check, build
except ImportError:
    from cad_pipeline import dump, inspect_source
    from engineering_gate import check, build


def main(destination):
    root = Path(destination).resolve()
    root.mkdir(parents=True, exist_ok=False)
    source = root / "fixture.png"
    image = Image.new("RGB", (800, 500), "white")
    draw = ImageDraw.Draw(image)
    draw.line([(100, 400), (600, 400)], fill="black", width=2)
    draw.ellipse((175, 225, 275, 325), outline="black", width=2)
    draw.text((200, 420), "100 mm", fill="black")
    draw.text((240, 260), "R10 mm", fill="black")
    image.save(source)
    # A second source deliberately has no metric information.
    unscaled = Image.new("RGB", (600, 400), "white")
    pen = ImageDraw.Draw(unscaled)
    pen.rectangle((80, 80, 480, 280), outline="black", width=3)
    unscaled.save(root / "unscaled.png")
    inspect_source(source, root / "inspection")
    statement = "Fixture sintetica de prueba; nominales definidos por el generador, no medicion fisica."
    evidence = [
        {"id": "D1", "source_id": "S1", "page": 1, "locator": "Base (0,0)-(100,0)",
         "kind": "dimension", "statement": statement + " 100 mm", "normalized_value": 100, "normalized_units": "mm"},
        {"id": "D2", "source_id": "S1", "page": 1, "locator": "Circulo R10",
         "kind": "dimension", "statement": statement + " R10 mm", "normalized_value": 10, "normalized_units": "mm"},
        {"id": "ORIGIN", "source_id": "S1", "page": 1, "locator": "Origen de la fixture y centro (25,25)",
         "kind": "datum", "statement": statement},
    ]
    def entity(identifier, kind, **fields):
        return {"id": identifier, "type": kind, "state": "VERIFICADO", "layer": "GEOMETRY",
                "evidence": statement,
                "definition": {"basis": "explicit_dimensions", "fully_constrained": True,
                               "evidence_ids": ["D1", "D2", "ORIGIN"], "parameters": list(fields)}, **fields}
    model = {
        "title": "Synthetic engineering fixture", "view": "Single synthetic view", "units": "mm",
        "source_image": "fixture.png",
        "calibration": {"status": "referenced", "references": [statement + " Base 100 mm"], "evidence_ids": ["D1"]},
        "registration": {"anchors": [{"cad": [0, 0], "pixel": [100, 400]},
                                      {"cad": [100, 0], "pixel": [600, 400]},
                                      {"cad": [0, 50], "pixel": [100, 150]}], "max_residual_px": 0.001},
        "entities": [entity("BASE", "LINE", start=[0, 0], end=[100, 0]),
                     entity("HOLE", "CIRCLE", center=[25, 25], radius=10)],
        "controls": [
            {"id": "C1", "entity": "BASE", "kind": "line_length", "expected": 100, "tolerance": 1e-6,
             "tolerance_basis": "Numerical fixture regression, not manufacturing tolerance",
             "role": "calibration", "evidence": statement, "evidence_id": "D1"},
            {"id": "C2", "entity": "HOLE", "kind": "radius", "expected": 10, "tolerance": 1e-6,
             "tolerance_basis": "Numerical fixture regression, not manufacturing tolerance",
             "role": "independent", "evidence": statement, "evidence_id": "D2"}],
        "coverage": {"review": "complete", "omitted": []}, "issues": [],
        "engineering": {"scope": "Only synthetic line and circle; headers are outside the fixture scope",
                        "comparison_tolerance": 1e-6, "tolerance_basis": "Synthetic numerical regression",
                        "sources": [{"id": "S1", "path": "fixture.png", "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}],
                        "evidence": evidence},
    }
    model['engineering']['uncertainty'] = {'mode': 'nominal_definition', 'physical_accuracy': 'unknown',
                                         'basis': 'Synthetic nominal geometry; no physical part measured'}
    model['engineering']['review_image'] = {'source_id': 'S1', 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                                          'transformation': 'Identity; generated synthetic PNG'}
    dump(root / "model.json", model)
    result = build(root / "model.json", root / "export")
    assert result["status"] == "DEFINED_REVIEW_PENDING"
    passed = ["Synthetic DXF exported and reopened; numerical controls passed; not marked validated"]
    cases = {
        "approximate": lambda m: m["entities"][0].update(state="APROXIMADO"),
        "reconstructed": lambda m: m["entities"][0].update(state="RECONSTRUIDO"),
        "unconstrained": lambda m: m["entities"][0]["definition"].update(fully_constrained=False),
        "no-tolerance": lambda m: m["engineering"].pop("comparison_tolerance"),
        "zero-tolerance": lambda m: m["engineering"].update(comparison_tolerance=0),
        "wrong-hash": lambda m: m["engineering"]["sources"][0].update(sha256="bad"),
        "wrong-page": lambda m: m["engineering"]["evidence"][0].update(page=2),
        "no-independent": lambda m: m["controls"][1].update(role="calibration"),
        "reused-calibration": lambda m: m["calibration"]["evidence_ids"].append("D2"),
        "dimension-conflict": lambda m: m["entities"][1].update(radius=11),
        "invented-control": lambda m: m["controls"][1].update(expected=11),
        "loose-tolerance": lambda m: m["controls"][1].update(tolerance=0.1),
        "missing-control": lambda m: m["controls"].pop(0),
        "missing-source": lambda m: m["engineering"]["sources"][0].update(path="absent.png"),
        "pending-coverage": lambda m: m["coverage"].update(review="pending"),
        "open-issues": lambda m: m["issues"].append("Unresolved dimension"),
        "two-anchors": lambda m: m["registration"]["anchors"].pop(),
        "collinear": lambda m: m["registration"]["anchors"].__setitem__(2, {"cad": [50, 0], "pixel": [350, 400]}),
        "unknown-unit": lambda m: m.update(units=None),
        "missing-evidence": lambda m: m["entities"][0]["definition"].update(evidence_ids=["ABSENT"]),
        "uncovered-parameter": lambda m: m["entities"][0]["definition"].update(parameters=["start"]),
        "fake-graphical-basis": lambda m: m["entities"][0]["definition"].update(basis="graphical_annotation"),
        "undocumented-derivation": lambda m: m["entities"][0]["definition"].update(basis="derived_constraints"),
        "duplicate-geometry": lambda m: m["entities"].append({**copy.deepcopy(m["entities"][0]), "id": "DUPLICATE"}),
    }
    for name, change in cases.items():
        candidate = copy.deepcopy(model)
        change(candidate)
        path = root / (name + ".json")
        dump(path, candidate)
        try:
            check(path)
        except (ValueError, KeyError, TypeError):
            passed.append(name + ": blocked")
        else:
            raise AssertionError("Accepted unsafe case: " + name)
    dump(root / "results.json", {"passed": passed, "scope": "Synthetic fixtures and metadata gate; not general plan fidelity"})
    print(json.dumps({"passed": len(passed), "checks": passed}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination")
    main(parser.parse_args().destination)

