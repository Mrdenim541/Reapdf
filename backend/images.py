"""Imágenes nuevas: datos originales PNG/JPEG y geometría en la página visible."""
import base64
import binascii
import struct
import pymupdf as fitz
from .engine import DocumentError, finite

MAX_IMAGE_BYTES = 2 * 1024 * 1024
MAX_IMAGE_PIXELS = 24_000_000
MAX_IMAGE_ENCODED = 4 * 1024 * 1024


def prepare_image(page, op):
    encoded = op.get('data')
    if not isinstance(encoded, str) or not encoded or len(encoded) > (MAX_IMAGE_BYTES + 2) // 3 * 4:
        raise DocumentError('La imagen debe ser PNG o JPEG de hasta 2 MB.')
    try:
        data = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise DocumentError('Los datos de la imagen no son válidos.') from exc
    if len(data) > MAX_IMAGE_BYTES or not (data.startswith(b'\x89PNG\r\n\x1a\n') or data.startswith(b'\xff\xd8\xff')):
        raise DocumentError('La imagen debe ser PNG o JPEG de hasta 2 MB.')
    try:
        width, height = image_dimensions(data)
        if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
            raise DocumentError('La imagen supera 24 millones de píxeles o no es válida.')
        # Validar las dimensiones antes de decodificar para acotar memoria.
        pixmap = fitz.Pixmap(data)
        if pixmap.width != width or pixmap.height != height:
            raise DocumentError('Dimensiones de imagen inconsistentes.')
    except DocumentError:
        raise
    except Exception as exc:
        raise DocumentError('No se pudo leer la imagen PNG o JPEG.') from exc
    points = op.get('points')
    if not isinstance(points, list) or len(points) != 2 or any(not isinstance(p, list) or len(p) != 2 or not all(finite(v) for v in p) for p in points):
        raise DocumentError('Posición de imagen no válida.')
    rect = fitz.Rect(*points[0], *points[1])
    if rect.width < 1 or rect.height < 1 or not page.rect.contains(rect):
        raise DocumentError('La imagen debe medir al menos 1 punto y permanecer dentro de la página.')
    return rect, data


def add_image(page, prepared):
    rect, data = prepared
    # La rotación de inserción compensa la rotación global de la hoja.
    rotation = page.rotation
    unrotated = rect * page.derotation_matrix
    # PyMuPDF calcula mal la traslación de CropBox al insertar con rotación.
    # La geometría se calcula antes y la rotación del documento se restaura.
    try:
        page.set_rotation(0)
        page.insert_image(unrotated, stream=data, rotate=rotation, keep_proportion=False, overlay=True)
    finally:
        page.set_rotation(rotation)


def image_dimensions(data):
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        if len(data) < 33 or data[8:16] != b'\x00\x00\x00\x0dIHDR':
            raise DocumentError('Cabecera PNG no válida.')
        return struct.unpack('>II', data[16:24])
    offset = 2
    while offset < len(data):
        if data[offset] != 0xff:
            break
        while offset < len(data) and data[offset] == 0xff:
            offset += 1
        if offset >= len(data):
            break
        marker = data[offset]; offset += 1
        if marker in {0xd8, 0x01} or 0xd0 <= marker <= 0xd7:
            continue
        if marker in {0xd9, 0xda} or offset + 2 > len(data):
            break
        length = int.from_bytes(data[offset:offset+2], 'big')
        if length < 2 or offset + length > len(data):
            break
        if marker in {0xc0,0xc1,0xc2,0xc3,0xc5,0xc6,0xc7,0xc9,0xca,0xcb,0xcd,0xce,0xcf}:
            if length < 8:
                break
            height, width = struct.unpack('>HH', data[offset+3:offset+7])
            return width, height
        offset += length
    raise DocumentError('Cabecera JPEG no válida.')
