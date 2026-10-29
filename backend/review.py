"""Anotaciones de revisión en coordenadas visibles; nunca eliminan contenido."""
import pymupdf as fitz
from .engine import DocumentError, finite

MARKUP = {"highlight", "underline", "strikeout"}


def prepare_review(page, op):
    color = op.get("color")
    if not isinstance(color, list) or len(color) != 3 or any(not finite(c) or not 0 <= c <= 1 for c in color):
        raise DocumentError("Color no válido.")

    def point(value):
        if not isinstance(value, list) or len(value) != 2 or not all(finite(v) for v in value):
            raise DocumentError("Coordenadas de anotación no válidas.")
        p = fitz.Point(*value)
        if not page.rect.contains(p):
            raise DocumentError("La anotación sale de la página.")
        return p * page.derotation_matrix

    if op["type"] == "note":
        content = op.get("content")
        if not isinstance(content, str) or not content.strip() or len(content) > 4000 or any(ord(c) < 32 and c not in "\n\t" for c in content):
            raise DocumentError("La nota requiere entre 1 y 4000 caracteres sin controles.")
        p = point(op.get("point"))
        # Mantener el icono completo dentro de la página, incluso al girarla.
        if not fitz.Rect(p.x, p.y, p.x + 20, p.y + 20) in (page.rect * page.derotation_matrix):
            raise DocumentError("Coloca la nota al menos a 20 puntos del borde.")
        return {"point": p, "content": content, "color": color}
    quads = op.get("quads")
    if not isinstance(quads, list) or not 1 <= len(quads) <= 500:
        raise DocumentError("Selecciona entre 1 y 500 fragmentos por marca.")
    prepared = []
    for value in quads:
        if not isinstance(value, list) or len(value) != 4:
            raise DocumentError("Región de texto no válida.")
        q = fitz.Quad([point(p) for p in value])
        if not q.is_convex or not q.is_rectangular or q.width < .1 or q.height < .1:
            raise DocumentError("Región de texto degenerada o no rectangular.")
        prepared.append(q)
    return {"quads": prepared, "color": color}


def add_review(page, kind, payload):
    if kind == "note":
        annot = page.add_text_annot(payload["point"], payload["content"], icon="Note")
        annot.set_info(title="Reapdf", content=payload["content"])
    else:
        method = {"highlight": page.add_highlight_annot, "underline": page.add_underline_annot,
                  "strikeout": page.add_strikeout_annot}[kind]
        annot = method(payload["quads"])
        annot.set_info(title="Reapdf")
    annot.set_colors(stroke=payload["color"])
    annot.update()


def review_selection(page):
    """Palabras sobre los ejes de página, con los cuatro vértices orientados tras girar página."""
    result, characters = [], []
    line_id = 0
    truncated = False
    for block in page.get_text("rawdict", sort=True, flags=fitz.TEXTFLAGS_RAWDICT & ~fitz.TEXT_PRESERVE_IMAGES)["blocks"]:
        for line in block.get("lines", []):
            line_id += 1
            if tuple(line["dir"]) not in {(1.,0.),(0.,1.),(-1.,0.),(0.,-1.)}:
                continue
            for span_id, span in enumerate(line["spans"]):
                for index, char in enumerate(span["chars"]):
                    if char["c"].isspace():
                        continue
                    quad = fitz.recover_char_quad(line["dir"], span, char) * page.rotation_matrix
                    if quad.width < .1 or quad.height < .1 or not all(page.rect.contains(p) for p in quad):
                        continue
                    if len(characters) == 100000:
                        truncated = True
                        continue
                    characters.append({"text": char["c"], "quad": [[p.x, p.y] for p in quad],
                                       "group": f"{line_id}:{span_id}", "index": index})
                group = []
                for char in span["chars"] + [{"c": " "}]:
                    if not char["c"].isspace():
                        group.append(char)
                    elif group:
                        rect = fitz.Rect(group[0]["bbox"])
                        for item in group[1:]:
                            rect |= fitz.Rect(item["bbox"])
                        quad = fitz.recover_quad(line["dir"], {**span, "bbox": tuple(rect)}) * page.rotation_matrix
                        if all(page.rect.contains(p) for p in quad):
                            result.append({"text": "".join(c["c"] for c in group),
                                           "quad": [[p.x, p.y] for p in quad]})
                        group = []
    return {"words": result, "characters": characters, "characters_truncated": truncated}


def review_words(page):
    return review_selection(page)["words"]
