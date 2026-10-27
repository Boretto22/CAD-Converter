"""Reimport a STEP and compare to independently supplied expectations in mm."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def check(path, expected=None):
    import cadquery as cq
    shapes = cq.importers.importStep(str(path)).vals()
    if not shapes:
        raise ValueError('STEP sin geometria')
    shape = cq.Compound.makeCompound(shapes)
    bounds = shape.BoundingBox()
    result = {"file": Path(path).name, "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
              "units": "mm", "valid": shape.isValid(), "solids": len(shape.Solids()),
              "volume_mm3": shape.Volume(), "bbox_mm": [bounds.xlen, bounds.ylen, bounds.zlen],
              "status": "REIMPORTADO; fidelidad pendiente de vistas y cotas", "checks": []}
    if expected:
        if expected["units"] != "mm":
            raise ValueError("Convertir expectativas a mm explícitamente")
        for key in ["solids", "volume_mm3", "bbox_mm"]:
            actual = result[key]
            target = expected[key]
            tolerance = 0 if key == "solids" else expected["tolerances"][key]
            actual = actual if isinstance(actual, list) else [actual]
            target = target if isinstance(target, list) else [target]
            if not math.isfinite(tolerance) or tolerance < 0 or len(actual) != len(target):
                raise ValueError("Expectativas o tolerancia no válidas")
            ok = all(math.isfinite(b) and abs(a-b) <= tolerance for a, b in zip(actual, target))
            result["checks"].append({"property": key, "pass": ok, "tolerance": tolerance})
        result["properties_match"] = result["valid"] and all(c["pass"] for c in result["checks"])
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("step")
    p.add_argument("--expected")
    p.add_argument("--output", required=True)
    a = p.parse_args()
    destination = Path(a.output)
    if destination.exists():
        raise FileExistsError(destination)
    expected = json.loads(Path(a.expected).read_text(encoding="utf-8-sig")) if a.expected else None
    result = check(a.step, expected)
    destination.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result["valid"] and result.get("properties_match", True) else 2)
