"""Evidence extraction and a conservative, agent-assisted 2D CAD export pipeline.

Commands never replace an existing output directory. See references/modelo.md.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image, ImageFilter, ImageOps


def dump(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def serial(obj):
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, bytes):
        return {"binary_bytes": len(obj), "sha256": hashlib.sha256(obj).hexdigest()}
    if isinstance(obj, dict):
        return {str(k): serial(v) for k, v in obj.items()}
    try:
        return [serial(v) for v in obj]
    except TypeError:
        return str(obj)


def versions():
    out = {}
    for p in ["PyMuPDF", "ezdxf", "Pillow", "numpy", "matplotlib", "reportlab", "cadquery"]:
        try:
            out[p] = importlib.metadata.version(p)
        except importlib.metadata.PackageNotFoundError:
            out[p] = None
    return out


def inspect_source(source, out, dpi=200):
    source, out = Path(source).resolve(), Path(out).resolve()
    if not source.is_file():
        raise ValueError("No existe el archivo de entrada")
    if not 72 <= dpi <= 600:
        raise ValueError("DPI de inspección fuera de 72..600")
    out.mkdir(parents=True, exist_ok=False)
    original = out / ("original" + source.suffix.lower())
    shutil.copy2(source, original)
    manifest = {"source": source.name, "sha256": sha(source), "versions": versions(),
                "created_utc": datetime.now(timezone.utc).isoformat(), "pages": [],
                "status": "INSPECCION; escala y semantica pendientes"}
    if source.suffix.lower() == ".pdf":
        import pymupdf as fitz
        with fitz.open(source) as doc:
            if doc.needs_pass:
                raise ValueError("PDF protegido: se necesita una copia accesible")
            manifest["pdf_optional_content_groups"] = serial(doc.get_ocgs())
            for index, page in enumerate(doc):
                stem = f"page-{index + 1:03}"
                pix = page.get_pixmap(dpi=dpi, alpha=False)
                pix.save(str(out / f"{stem}.png"))
                drawings = page.get_drawings()
                texts = page.get_text("dict")
                annotations = [{"info": a.info, "rect": list(a.rect), "type": a.type}
                               for a in (page.annots() or [])]
                dump(out / f"{stem}-vectors.json", serial(drawings))
                dump(out / f"{stem}-text.json", serial(texts))
                dump(out / f"{stem}-annotations.json", serial(annotations))
                manifest["pages"].append({"page": index + 1, "png": f"{stem}.png",
                    "rect_pt": list(page.rect), "cropbox_pt": list(page.cropbox),
                    "rotation": page.rotation, "rotation_matrix": list(page.rotation_matrix),
                    "dpi": dpi, "pixel_size": [pix.width, pix.height],
                    "vector_paths": len(drawings), "image_instances": len(page.get_image_info()),
                    "text_blocks": sum(b["type"] == 0 for b in texts["blocks"]),
                    "annotations": len(annotations), "review": "PENDIENTE"})
    else:
        with Image.open(source) as im:
            for index in range(getattr(im, "n_frames", 1)):
                im.seek(index)
                exif_orientation = im.getexif().get(274)
                page = ImageOps.exif_transpose(im.copy()).convert("RGB")
                stem = f"page-{index + 1:03}"
                page.save(out / f"{stem}.png")
                manifest["pages"].append({"page": index + 1, "png": f"{stem}.png",
                    "pixel_size": list(page.size), "exif_orientation_applied": exif_orientation,
                    "dpi_metadata_unverified": serial(im.info.get("dpi")),
                    "classification": "raster", "review": "PENDIENTE"})
    dump(out / "manifest.json", manifest)
    return manifest


def finite_tree(obj):
    if isinstance(obj, float) and not math.isfinite(obj):
        raise ValueError("Coordenada o valor no finito")
    if isinstance(obj, dict):
        for v in obj.values():
            finite_tree(v)
    if isinstance(obj, list):
        for v in obj:
            finite_tree(v)


def registration(model):
    """Similarity transform: CAD y-up -> image y-down. No free deformation."""
    anchors = model["registration"]["anchors"]
    if len(anchors) < 2:
        raise ValueError("Se necesitan al menos dos anclajes distintos")
    rows, vals = [], []
    for p in anchors:
        x, y = p["cad"]
        u, v = p["pixel"]
        rows.extend([[x, -y, 1, 0], [-y, -x, 0, 1]])
        vals.extend([u, v])
    a = np.array(rows, float)
    if np.linalg.matrix_rank(a) != 4:
        raise ValueError("Anclajes degenerados")
    k, _, _, _ = np.linalg.lstsq(a, np.array(vals), rcond=None)
    aa, bb, tx, ty = k
    scale = math.hypot(aa, bb)
    if scale <= 0:
        raise ValueError("Escala nula")
    transform = np.array([[aa, -bb, tx], [-bb, -aa, ty], [0, 0, 1]])
    residuals = np.linalg.norm((a @ k - vals).reshape(-1, 2), axis=1)
    max_allowed = model["registration"]["max_residual_px"]
    if max_allowed < 0 or float(residuals.max()) > max_allowed:
        raise ValueError("Registro incompatible con el residual permitido")
    return transform, {"matrix_cad_to_pixel": transform.tolist(), "pixel_per_unit": scale,
        "residual_max_px": float(residuals.max()),
        "residual_rms_px": float(np.sqrt(np.mean(residuals ** 2))),
        "note": "Residual de ajuste, no validacion dimensional independiente"}


def make_entity(space, e, attr):
    kind = e["type"]
    if kind == "LINE":
        if math.dist(e["start"], e["end"]) == 0:
            raise ValueError("LINE de longitud cero")
        return space.add_line(e["start"], e["end"], dxfattribs=attr)
    if kind == "LWPOLYLINE":
        if len(e["points"]) < 2:
            raise ValueError("Polilinea insuficiente")
        return space.add_lwpolyline(e["points"], format="xyb", close=e.get("closed", False), dxfattribs=attr)
    if kind in {"CIRCLE", "ARC"}:
        if e["radius"] <= 0:
            raise ValueError("Radio no positivo")
        if kind == "CIRCLE":
            return space.add_circle(e["center"], e["radius"], dxfattribs=attr)
        return space.add_arc(e["center"], e["radius"], e["start_angle"], e["end_angle"], dxfattribs=attr)
    if kind == "ELLIPSE":
        return space.add_ellipse(e["center"], major_axis=e["major_axis"], ratio=e["ratio"],
            start_param=e.get("start_param", 0), end_param=e.get("end_param", 2 * math.pi), dxfattribs=attr)
    if kind == "SPLINE":
        # Explicit control points/knots; never silently use fit-point approximation.
        return space.add_open_spline(e["control_points"], degree=e["degree"],
            knots=e["knots"], dxfattribs=attr)
    if kind == "TEXT":
        return space.add_text(e["text"], dxfattribs={**attr, "insert": e["insert"],
            "height": e["height"], "rotation": e.get("rotation", 0)})
    if kind == "MTEXT":
        return space.add_mtext(e["text"], dxfattribs={**attr, "insert": e["insert"],
            "char_height": e["height"], "width": e.get("width", 0), "rotation": e.get("rotation", 0)})
    if kind == "HATCH":
        h = space.add_hatch(color=attr["color"], dxfattribs=attr)
        h.paths.add_polyline_path(e["boundary"], is_closed=True)
        if e.get("pattern"):
            h.set_pattern_fill(e["pattern"], scale=e.get("pattern_scale", 1), angle=e.get("pattern_angle", 0))
        return h
    if kind == "DIMENSION":
        dim = space.add_linear_dim(base=e["base"], p1=e["p1"], p2=e["p2"],
            angle=e.get("angle", 0), dimstyle="EZDXF", dxfattribs=attr,
            override={"dimtxt": e["text_height"], "dimasz": e["arrow_size"],
                      "dimdec": e.get("decimals", 2), "dimlfac": 1})
        # A literal override could hide a geometric contradiction: keep calculated dimension.
        dim.render()
        return dim.dimension
    raise ValueError(f"Tipo no soportado: {kind}. Ampliar exportador; no omitir.")


def measured_control(c, entity):
    kind = c["kind"]
    if kind == "line_length" and entity.dxftype() == "LINE":
        return entity.dxf.start.distance(entity.dxf.end)
    if kind == "radius" and entity.dxftype() in {"CIRCLE", "ARC"}:
        return float(entity.dxf.radius)
    if kind == "diameter" and entity.dxftype() in {"CIRCLE", "ARC"}:
        return 2 * float(entity.dxf.radius)
    if kind == "dimension" and entity.dxftype() == "DIMENSION":
        return float(entity.get_measurement())
    raise ValueError(f"Control no soportado o tipo incompatible: {kind}")


def render_registered(doc, image_size, transform, destination):
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt
    from ezdxf.addons.drawing import RenderContext, Frontend
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    from ezdxf.addons.drawing.config import Configuration, ColorPolicy, BackgroundPolicy
    width, height = image_size
    inverse = np.linalg.inv(transform)
    corners = (inverse @ np.array([[0, width, width, 0], [0, 0, height, height], [1, 1, 1, 1]]))[:2]
    xmin, ymin = corners.min(axis=1)
    xmax, ymax = corners.max(axis=1)
    fig = plt.figure(figsize=(width / 100, height / 100), dpi=100, facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1])
    config = Configuration(color_policy=ColorPolicy.BLACK, background_policy=BackgroundPolicy.WHITE)
    Frontend(RenderContext(doc), MatplotlibBackend(ax, adjust_figure=False), config=config).draw_layout(doc.modelspace(), finalize=True)
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect("auto")
    ax.set_axis_off()
    fig.canvas.draw()
    cad = Image.fromarray(np.asarray(fig.canvas.buffer_rgba())).convert("RGB")
    plt.close(fig)
    # Map every original pixel to the native CAD-render canvas, preserving the fixed registration.
    to_canvas = np.array([[width / (xmax-xmin), 0, -xmin*width/(xmax-xmin)],
                         [0, -height/(ymax-ymin), ymax*height/(ymax-ymin)], [0, 0, 1]])
    affine = (to_canvas @ inverse)[:2].ravel().tolist()
    cad = cad.transform((width, height), Image.Transform.AFFINE, affine,
                        resample=Image.Resampling.BICUBIC, fillcolor="white")
    cad.save(destination)
    return cad


def compare_images(source, cad, out, band_px):
    if not isinstance(band_px, int) or not 0 <= band_px <= 20:
        raise ValueError("Banda visual debe ser un entero entre 0 y 20 pixeles")
    a = np.asarray(source.convert("L")) < 180
    b = np.asarray(cad.convert("L")) < 180
    def dilated(mask):
        image = Image.fromarray((mask * 255).astype("uint8"))
        return np.asarray(image.filter(ImageFilter.MaxFilter(2 * band_px + 1))) > 0
    only_source = a & ~dilated(b)
    only_cad = b & ~dilated(a)
    overlay = np.full((*a.shape, 3), 255, dtype="uint8")
    overlay[a] = [0, 150, 210]
    overlay[b] = [220, 50, 130]
    overlay[a & b] = [35, 35, 35]
    Image.fromarray(overlay).save(out / "superposicion.png")
    diff = np.full((*a.shape, 3), 255, dtype="uint8")
    diff[a | b] = [220, 220, 220]
    diff[only_source] = [0, 150, 210]
    diff[only_cad] = [220, 50, 130]
    Image.fromarray(diff).save(out / "diferencias.png")
    return {"threshold_gray": 180, "band_px": band_px,
            "source_ink_pixels": int(a.sum()), "cad_ink_pixels": int(b.sum()),
            "source_uncovered_pct": float(100*only_source.sum()/a.sum()) if a.sum() else None,
            "cad_unmatched_pct": float(100*only_cad.sum()/b.sum()) if b.sum() else None,
            "meaning": "Diagnostico de tinta; NO porcentaje de fidelidad dimensional"}


def report_pdf(model, report, out):
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.colors import HexColor
    styles = getSampleStyleSheet()
    styles["Title"].textColor = HexColor("#17344d")
    styles["Normal"].fontSize = 10
    styles["Normal"].leading = 14
    story = []
    def para(text, style="Normal"):
        story.append(Paragraph(escape(str(text)), styles[style]))
        story.append(Spacer(1, 7))
    para("Engineering CAD Converter / Comprobación", "Title")
    para(model["title"], "Heading2")
    para("PROVISIONAL - requiere revisión visual y de cobertura")
    para(f"Vista: {model['view']} · Unidad: {model['units']} · Entidades: {report['entity_count']}")
    para("Calibración", "Heading2")
    for ref in model["calibration"]["references"]:
        para(ref)
    para(f"Registro: residual máximo {report['registration']['residual_max_px']:.4g} px. Es un residual de ajuste, no una validación independiente.")
    para("Controles medidos en el DXF reabierto", "Heading2")
    if not report["controls"]:
        para("SIN CONTROLES INDEPENDIENTES. La precisión dimensional no está comprobada.")
    for c in report["controls"]:
        para(f"{c['id']} [{c['role']}]: esperado {c['expected']}, CAD {c['measured']:.6g}, diferencia {c['delta']:.6g}, tolerancia {c['tolerance']} {model['units']} -> {c['result']}")
    para("Incertidumbre", "Heading2")
    uncertainty = report.get('uncertainty') or {}
    if uncertainty.get('mode') == 'nominal_definition':
        para('Definición nominal. Exactitud física desconocida; no se asigna incertidumbre cero.')
    elif uncertainty.get('mode') == 'bounded_measurement':
        para(f"Límite de error de longitud: {uncertainty['length_error_bound']:.6g} {uncertainty['units']}. Condicionado a componentes declarados; no es intervalo estadístico.")
    else:
        para('Sin evaluación de incertidumbre. No usar como validación dimensional física.')
    if uncertainty.get('basis'):
        para(uncertainty['basis'])
    para("Alcance y pendientes", "Heading2")
    for item in report["limitations"] + model.get("issues", []):
        para(item)
    para("Diagnóstico visual", "Heading2")
    v = report["visual"]
    pct = lambda x: "no evaluable" if x is None else f"{x:.2f}%"
    para(f"Banda {v['band_px']} px. Tinta original sin cobertura: {pct(v['source_uncovered_pct'])}. Tinta CAD sin correspondencia: {pct(v['cad_unmatched_pct'])}. No representan precisión dimensional.")
    for filename, title, caption in [
        ("fuente.png", "01 / Evidencia original", "Referencia utilizada; no se modifica para forzar coincidencias."),
        ("cad.png", "02 / DXF reabierto", "Vista de comprobación; el archivo editable se entrega por separado."),
        ("superposicion.png", "03 / Superposición", "Cian: original. Magenta: CAD. Oscuro: coincidencia exacta de tinta."),
        ("diferencias.png", "04 / Diferencias fuera de banda", "Cian: falta cobertura CAD. Magenta: trazo CAD sin correspondencia. Gris: tinta restante.")]:
        story.append(PageBreak())
        para(title, "Heading1")
        para(caption)
        with Image.open(out / filename) as im:
            w, h = im.size
        factor = min(495/w, 615/h)
        story.append(RLImage(str(out / filename), width=w*factor, height=h*factor))
        para("Comprobación visual. Esta página está ajustada al papel; no medir con regla.")
    def footer(c, doc):
        c.setFont("Helvetica", 8)
        c.drawString(42, 24, "Engineering CAD Converter | " + str(doc.page) + " | PROVISIONAL")
    SimpleDocTemplate(str(out / "comprobacion.pdf"), pagesize=(595, 842),
        rightMargin=42, leftMargin=42, topMargin=38, bottomMargin=42).build(story, onFirstPage=footer, onLaterPages=footer)


def build(model_path, out):
    import ezdxf
    model_path, out = Path(model_path).resolve(), Path(out).resolve()
    model = json.loads(model_path.read_text(encoding="utf-8-sig"))
    finite_tree(model)
    units = {"mm": 4, "cm": 5, "m": 6, "in": 1}
    if model.get("units") not in units:
        raise ValueError("BLOQUEADO: falta una unidad comprobada (mm, cm, m, in)")
    cal = model.get("calibration", {})
    if cal.get("status") != "referenced" or not cal.get("references"):
        raise ValueError("BLOQUEADO: falta una referencia explícita de escala")
    if not model.get("entities"):
        raise ValueError("No hay geometría editable")
    transform, reg = registration(model)
    src = (model_path.parent / model["source_image"]).resolve()
    uncertainty = None
    if model.get('engineering'):
        try:
            from .assurance import validate as uncertainty_check
        except ImportError:
            from assurance import validate as uncertainty_check
        uncertainty = uncertainty_check(model, model_path.parent)
    image = Image.open(src).convert("RGB")
    if max(image.size) > 7000:
        raise ValueError("Render mayor de 7000 px: crear copia de revisión y transformar anclajes")
    doc = ezdxf.new("R2013", setup=True)
    doc.units = units[model["units"]]
    doc.appids.new("CAD_FIEL")
    msp = doc.modelspace()
    handles = {}
    seen = set()
    duplicate_ids = []
    for e in model["entities"]:
        if e["id"] in handles:
            raise ValueError("ID de entidad duplicado")
        if e.get("state") != "VERIFICADO" or not e.get("evidence"):
            raise ValueError("Cada entidad necesita estado y evidencia")
        layer = e["state"] + "__" + e["layer"]
        if re.search(r'[<>/\\":;?*|=]', layer):
            raise ValueError("Nombre de capa no válido")
        color = 7
        if layer not in doc.layers:
            doc.layers.new(layer, dxfattribs={"color": color,
                "linetype": "CONTINUOUS"})
        entity = make_entity(msp, e, {"layer": layer, "color": 256})
        # Chunk XDATA strings conservatively to keep DXF string limits safe.
        evidence = json.dumps({"id": e["id"], "evidence": e["evidence"], "state": e["state"]}, ensure_ascii=True)
        entity.set_xdata("CAD_FIEL", [(1000, evidence[i:i+180]) for i in range(0, len(evidence), 180)])
        handles[e["id"]] = entity.dxf.handle
        signature = json.dumps({k: v for k, v in e.items() if k not in {"id", "evidence", "state", "layer"}}, sort_keys=True)
        if signature in seen:
            duplicate_ids.append(e["id"])
        seen.add(signature)
    # All unsupported entities/invalid data fail before creating the deliverable directory.
    out.mkdir(parents=True, exist_ok=False)
    doc.saveas(out / "plano.dxf")
    reopened = ezdxf.readfile(out / "plano.dxf")
    auditor = reopened.audit()
    controls = []
    for c in model.get("controls", []):
        if c.get("role") not in {"calibration", "independent"} or not c.get("evidence") or not c.get("tolerance_basis"):
            raise ValueError("Control sin rol, evidencia o procedencia de tolerancia")
        if c["tolerance"] < 0:
            raise ValueError("Tolerancia negativa")
        measured = measured_control(c, reopened.entitydb[handles[c["entity"]]])
        delta = measured - c["expected"]
        controls.append({**c, "measured": measured, "delta": delta,
            "result": "PASS" if abs(delta) <= c["tolerance"] else "FAIL"})
    cad = render_registered(reopened, image.size, transform, out / "cad.png")
    image.save(out / "fuente.png")
    visual = compare_images(image, cad, out, model.get("visual_band_px", 2))
    limitations = ["Exportador de una vista. Revisar cobertura de todas las páginas y vistas del original.",
        "La auditoría DXF no verifica topología, autointersecciones, asociaciones ni semántica.",
        "No se ha probado en un segundo programa CAD. Revisar fuentes, cotas y rayados.",
        "La superposición incluye texto y ruido. Sus porcentajes no son precisión dimensional."]
    if len(model["registration"]["anchors"]) == 2:
        limitations.append("Solo dos anclajes: no se verifica distorsión ni perspectiva.")
    if not any(c["role"] == "independent" for c in controls):
        limitations.append("Faltan cotas de control independientes.")
    if duplicate_ids:
        limitations.append("Posibles entidades duplicadas: " + ", ".join(duplicate_ids))
    report = {"status": "PROVISIONAL", "title": model["title"], "view": model["view"],
        "units": model["units"], "model_sha256": sha(model_path), "source_image_sha256": sha(src),
        "dxf_sha256": sha(out / "plano.dxf"), "versions": versions(), "registration": reg,
        "entity_count": len(reopened.modelspace()), "entity_types": dict(Counter(e.dxftype() for e in reopened.modelspace())),
        "entity_handles": handles, "audit_errors": len(auditor.errors), "audit_fixes": len(auditor.fixes),
        "controls": controls, "visual": visual, "limitations": limitations, "issues": model.get("issues", []),
        "coverage": model.get("coverage", "PENDIENTE"), "visual_review": "PENDIENTE", "uncertainty": uncertainty}
    dump(out / "informe.json", report)
    shutil.copy2(model_path, out / "modelo-original.json")
    portable = dict(model)
    portable["source_image"] = "fuente.png"
    dump(out / "modelo-reproducible.json", portable)
    lines = ["# Informe de diferencias", "", "Estado: PROVISIONAL", "", model["title"], "",
             "## Controles medidos en el DXF reabierto", ""]
    lines += [f"- {c['id']}: {c['result']}; esperado {c['expected']}; medido {c['measured']:.6g}; diferencia {c['delta']:.6g} {model['units']}." for c in controls]
    lines += ["", "## Límites y pendientes", ""] + ["- " + s for s in limitations + model.get("issues", [])]
    lines += ['', '## Incertidumbre', '', json.dumps(uncertainty, ensure_ascii=False, indent=2)]
    (out / "informe.md").write_text("\n".join(lines), encoding="utf-8")
    report_pdf(model, report, out)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    a = sub.add_parser("inspect")
    a.add_argument("source")
    a.add_argument("output")
    a.add_argument("--dpi", type=int, default=200)
    b = sub.add_parser("build")
    b.add_argument("model")
    b.add_argument("output")
    args = p.parse_args()
    result = inspect_source(args.source, args.output, args.dpi) if args.command == "inspect" else build(args.model, args.output)
    print(json.dumps({"output": str(Path(args.output).resolve()), "status": result["status"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
