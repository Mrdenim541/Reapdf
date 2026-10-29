"""Motor experimental. Las operaciones siempre generan una copia del original."""
import math
import pymupdf as fitz

MAX_PAGES = 500
MAX_OPERATIONS = 1000

class DocumentError(ValueError):
    pass

def open_pdf(data: bytes):
    doc = None
    try:
        doc = fitz.open(stream=data, filetype="pdf")
        if doc.needs_pass:
            raise DocumentError("Este prototipo no admite PDF con contraseña.")
        if not 1 <= len(doc) <= MAX_PAGES:
            raise DocumentError(f"Se admiten documentos de 1 a {MAX_PAGES} páginas.")
        if any(max(p.rect.width, p.rect.height) > 6000 for p in doc):
            raise DocumentError("Este prototipo no admite páginas de más de 6000 puntos.")
        return doc
    except DocumentError:
        if doc is not None:
            doc.close()
        raise
    except Exception as exc:
        if doc is not None:
            doc.close()
        raise DocumentError("No se pudo abrir el PDF. Comprueba que no esté dañado.") from exc

def spans(page):
    from .text_style import SOURCE_FONTS
    result = []
    for bi, block in enumerate(page.get_text("dict")["blocks"]):
        for li, line in enumerate(block.get("lines", [])):
            for si, span in enumerate(line["spans"]):
                # Solo líneas simples, horizontales, sin rotación y con fuente base conocida.
                supported_font = span["font"] in SOURCE_FONTS
                editable = (page.rotation == 0 and line["dir"] == (1.0, 0.0)
                            and len(line["spans"]) == 1 and supported_font
                            and span.get("alpha", 255) == 255 and 6 <= span["size"] <= 144)
                result.append({"id": f"{bi}:{li}:{si}", "text": span["text"],
                               "bbox": list(span["bbox"]), "origin": list(span["origin"]),
                               "size": span["size"], "font": span["font"],
                               "color": span["color"], "font_key": SOURCE_FONTS.get(span["font"]), "editable": editable})
    return result

def metadata(doc):
    from .page_labels import visible_labels
    labels=visible_labels(doc)
    toc = doc.get_toc()
    bookmarks = [{"level": row[0], "title": row[1],
                  "page": row[2] - 1 if 1 <= row[2] <= len(doc) else None}
                 for row in toc[:2000]]
    return {"bookmarks": bookmarks, "bookmarks_truncated": len(toc) > 2000,
            "pages": [{"width": p.rect.width, "height": p.rect.height,
                        "rotation": p.rotation, "label": labels[p.number]} for p in doc],
            "signed": doc.get_sigflags() > 0,
            "can_organize": bool(doc.permissions & (fitz.PDF_PERM_ASSEMBLE | fitz.PDF_PERM_MODIFY)),
            "can_extract": bool(doc.permissions & fitz.PDF_PERM_COPY),
            "can_print": bool(doc.permissions & fitz.PDF_PERM_PRINT and doc.permissions & fitz.PDF_PERM_PRINT_HQ),
            "can_fill": bool(doc.permissions & fitz.PDF_PERM_FORM),
            "can_copy": bool(doc.permissions & fitz.PDF_PERM_COPY),
            "can_edit": bool(doc.permissions & fitz.PDF_PERM_MODIFY),
            "can_annotate": bool(doc.permissions & fitz.PDF_PERM_ANNOTATE)}

def finite(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)

def export_pdf(data, operations):
    if not isinstance(operations, list) or len(operations) > MAX_OPERATIONS:
        raise DocumentError("Demasiadas operaciones o formato no válido.")
    if any(isinstance(op,dict) and op.get('type')=='form_rules' for op in operations):
        from .form_rules import resolve_rules
        operations=resolve_rules(data,operations)[0]
    with open_pdf(data) as doc:
        if not operations:
            return data
        if doc.get_sigflags() > 0:
            raise DocumentError("No se modifican PDF firmados en este prototipo.")
        from .existing_annotations import related_annotations, prepare_existing, apply_existing
        related = related_annotations(doc) if any(isinstance(op, dict) and op.get('type') == 'existing_annot' for op in operations) else set()
        prepared = []
        image_encoded = 0
        seen = set()
        for op in operations:
            if not isinstance(op, dict):
                raise DocumentError("Operación no válida.")
            number = op.get("page")
            if type(number) is not int or not 0 <= number < len(doc):
                raise DocumentError("Página no válida.")
            page = doc[number]
            kind = op.get("type")
            if kind=='watermark':
                from .watermarks import prepare_watermark
                if not doc.permissions & fitz.PDF_PERM_MODIFY or kind in seen:raise DocumentError('No se permite esta marca de agua o existe otra configuración.')
                seen.add(kind);prepared.append((number,kind,prepare_watermark(doc,op),None))
            elif kind=='form_fill':
                from .forms import prepare_fill
                if kind in seen:raise DocumentError('Solo se admite una configuración de formulario.')
                seen.add(kind)
                prepared.append((number,kind,prepare_fill(doc,op.get('values')),None))
            elif kind in {'bookmarks','header_footer'}:
                if not doc.permissions & fitz.PDF_PERM_MODIFY:
                    raise DocumentError('El documento no permite modificar el índice o el contenido de página.')
                if kind in seen:raise DocumentError('Solo se admite una configuración consolidada de este tipo.')
                seen.add(kind)
                if kind=='bookmarks':
                    from .bookmarks import prepare_bookmarks
                    payload=prepare_bookmarks(doc,op.get('items'))
                else:
                    from .headers import prepare_headers
                    payload=prepare_headers(doc,op)
                prepared.append((number,kind,payload,None))
            elif kind in {'textbox', 'stamp', 'link'}:
                from .content_tools import prepare_content
                required = fitz.PDF_PERM_ANNOTATE if kind == 'stamp' else fitz.PDF_PERM_MODIFY
                if not doc.permissions & required:
                    raise DocumentError('El documento no permite esta modificación.')
                prepared.append((number, kind, prepare_content(doc, page, op), None))
            elif kind == "image":
                from .images import prepare_image, MAX_IMAGE_ENCODED
                if not doc.permissions & fitz.PDF_PERM_MODIFY:
                    raise DocumentError("El documento no permite modificar contenido.")
                image_encoded += len(op.get('data', '')) if isinstance(op.get('data'), str) else 0
                if image_encoded > MAX_IMAGE_ENCODED:
                    raise DocumentError("Las imágenes de la sesión superan 4 MB codificados. Exporta y vuelve a abrir el PDF antes de insertar más.")
                prepared.append((number, kind, prepare_image(page, op), None))
            elif kind == "existing_annot":
                payload = prepare_existing(doc, page, op, related)
                key = (number, 'existing', payload[0])
                if key in seen:
                    raise DocumentError("Una anotación existente solo admite una operación consolidada por exportación.")
                seen.add(key)
                prepared.append((number, kind, payload, None))
            elif kind == "text":
                if not doc.permissions & fitz.PDF_PERM_MODIFY:
                    raise DocumentError("El documento no permite modificar contenido.")
                if any(a.type[0] == fitz.PDF_ANNOT_REDACT for a in page.annots() or []):
                    raise DocumentError("La página contiene censuras pendientes. No se editará texto en ella.")
                if not isinstance(op.get("span_id"), str):
                    raise DocumentError("Identificador de texto no válido.")
                key = (number, op.get("span_id"))
                if key in seen:
                    raise DocumentError("Una línea no puede reemplazarse dos veces en la misma exportación.")
                seen.add(key)
                all_spans = spans(page)
                source = next((s for s in all_spans if s["id"] == op.get("span_id")), None)
                if not source or not source["editable"]:
                    raise DocumentError("Esta línea no es compatible con la edición inicial.")
                replacement = op.get("text")
                if not isinstance(replacement, str) or len(replacement) > 2000 or any(ord(c) < 32 or ord(c) > 255 for c in replacement):
                    raise DocumentError("Usa una sola línea con caracteres latinos compatibles.")
                box = fitz.Rect(source["bbox"])
                if any(s["id"] != source["id"] and (box & fitz.Rect(s["bbox"])).get_area() > 0.1 for s in all_spans):
                    raise DocumentError("La región se cruza con otro texto; no se modificará automáticamente.")
                from .text_style import prepare_text_style
                source = prepare_text_style(page, source, replacement, op, all_spans)
                prepared.append((number, kind, source, replacement))
            elif kind in {"highlight", "underline", "strikeout", "note"}:
                from .review import prepare_review
                if not doc.permissions & fitz.PDF_PERM_ANNOTATE:
                    raise DocumentError("El documento no permite anotaciones.")
                prepared.append((number, kind, prepare_review(page, op), None))
            elif kind in {"ink", "line", "arrow", "rectangle"}:
                if not doc.permissions & fitz.PDF_PERM_ANNOTATE:
                    raise DocumentError("El documento no permite anotaciones.")
                pts, color, width = op.get("points"), op.get("color"), op.get("width")
                if not isinstance(pts, list) or not 2 <= len(pts) <= 10000:
                    raise DocumentError("Trazo no válido.")
                if kind != "ink" and len(pts) != 2:
                    raise DocumentError("La figura requiere dos puntos.")
                if not isinstance(color, list) or len(color) != 3 or any(not finite(c) or not 0 <= c <= 1 for c in color):
                    raise DocumentError("Color no válido.")
                if not finite(width) or not 0.5 <= width <= 12:
                    raise DocumentError("Grosor no válido.")
                for pt in pts:
                    if not isinstance(pt, list) or len(pt) != 2 or not all(finite(v) for v in pt) or not page.rect.contains(fitz.Point(*pt)):
                        raise DocumentError("El trazo sale de la página.")
                if kind in {"line", "arrow"} and math.dist(*pts) < 1:
                    raise DocumentError("La línea es demasiado corta.")
                if kind == "rectangle" and any(abs(pts[0][i] - pts[1][i]) < 1 for i in (0, 1)):
                    raise DocumentError("El rectángulo requiere ancho y alto.")
                prepared.append((number, kind, pts, (color, width)))
            else:
                raise DocumentError("Tipo de operación no compatible.")
        text_boxes = [(number, source['new_box']) for number, kind, source, replacement in prepared if kind == 'text' and replacement]
        for i, (number, box) in enumerate(text_boxes):
            if any(other_number == number and (box & other).get_area() > .1 for other_number, other in text_boxes[i+1:]):
                raise DocumentError('Dos textos editados se superponen. Reduce su tamaño.')
        # Conservar los xref de la fuente hasta terminar todos sus cambios.
        for number, kind, payload, _ in prepared:
            if kind == 'existing_annot':
                apply_existing(doc[number], payload)
        # Eliminar texto antes de dibujar anotaciones nuevas.
        for number, kind, source, replacement in prepared:
            if kind != "text":
                continue
            page = doc[number]
            page.add_redact_annot(source["bbox"], fill=False, cross_out=False)
            page.apply_redactions(images=0, graphics=0, text=0)
            if replacement:
                page.insert_text(source["origin"], replacement, fontsize=source["target_size"], fontname=source["target_font"], color=source["target_color"])
        for number, kind, pts, style in prepared:
            if kind in {"text", "existing_annot"}:
                continue
            page = doc[number]
            if kind=='watermark':
                from .watermarks import apply_watermark
                apply_watermark(doc,pts)
                continue
            if kind=='form_fill':
                from .forms import apply_fill
                apply_fill(doc,pts)
                continue
            if kind=='bookmarks':
                from .bookmarks import apply_bookmarks
                apply_bookmarks(doc,pts)
                continue
            if kind=='header_footer':
                from .headers import apply_headers
                apply_headers(doc,pts)
                continue
            if kind in {'textbox','stamp','link'}:
                from .content_tools import add_content
                add_content(page, kind, pts)
                continue
            if kind == "image":
                from .images import add_image
                add_image(page, pts)
                continue
            if kind in {"highlight", "underline", "strikeout", "note"}:
                from .review import add_review
                add_review(page, kind, pts)
                continue
            points = [tuple(fitz.Point(*p) * page.derotation_matrix) for p in pts]
            if kind == "ink":
                annot = page.add_ink_annot([points])
            elif kind in {"line", "arrow"}:
                annot = page.add_line_annot(points[0], points[1])
                if kind == "arrow":
                    annot.set_line_ends(fitz.PDF_ANNOT_LE_NONE, fitz.PDF_ANNOT_LE_CLOSED_ARROW)
            else:
                rect = fitz.Rect(points[0], points[1]).normalize()
                annot = page.add_rect_annot(rect)
            annot.set_colors(stroke=style[0])
            annot.set_border(width=style[1])
            if kind == "rectangle":
                # Actualizar primero /RD al nuevo grosor. set_rect usa ese margen
                # para que el centro del borde coincida con la figura dibujada.
                annot.update()
                annot.set_rect(rect)
            annot.set_info(title="Reapdf", content={"ink": "Trazo libre", "line": "Línea", "arrow": "Flecha", "rectangle": "Rectángulo"}[kind])
            annot.update()
        return doc.tobytes(encryption=fitz.PDF_ENCRYPT_KEEP,garbage=4, deflate=True)
