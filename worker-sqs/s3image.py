import boto3
from botocore.exceptions import ClientError
from PIL import Image, ImageFilter, ImageOps
import os

s3_client = boto3.client('s3')

# ── SUBIR ──────────────────────────────────────────────
def upload_file(file_name, bucket, object_name=None, extra_args={}):
    if object_name is None:
        object_name = os.path.basename(file_name)
    try:
        s3_client.upload_file(file_name, bucket, object_name, ExtraArgs=extra_args)
        return True
    except ClientError as e:
        print("Error s3:", e)
        return False

# ── DESCARGAR ──────────────────────────────────────────
def download_file(bucket, key, file_name):
    s3_client.download_file(Bucket=bucket, Key=key, Filename=file_name)

# ── REDIMENSIONAR ──────────────────────────────────────
def resize_image(file_name, new_name, scale=0.5):
    im = Image.open(file_name)
    new_size = (round(im.size[0] * scale), round(im.size[1] * scale))
    resized = im.resize(new_size, Image.LANCZOS)
    resized.save(new_name)

# ── NORMALIZAR MODO ─────────────────────────────────────
def _normalize(im, fmt):
    """Convierte el modo de la imagen según el formato destino."""
    fmt = fmt.upper()
    if fmt in ('JPEG',):
        # JPEG no soporta transparencia ni paleta
        if im.mode != 'RGB':
            return im.convert('RGB')
    elif fmt == 'GIF':
        # GIF requiere paleta P o L
        if im.mode not in ('P', 'L'):
            return im.convert('P')
    elif fmt in ('PNG', 'WEBP', 'BMP'):
        # Estos soportan RGB y RGBA, convertir paleta a RGB
        if im.mode == 'P':
            return im.convert('RGBA')
        if im.mode == 'L':
            return im.convert('RGB')
    return im

# ── SEPIA ───────────────────────────────────────────────
def _apply_sepia(im):
    im = im.convert('RGB')
    gray = ImageOps.grayscale(im)
    sepia = Image.new('RGB', gray.size)
    pixels = gray.load()
    out = sepia.load()
    for y in range(gray.size[1]):
        for x in range(gray.size[0]):
            v = pixels[x, y]
            out[x, y] = (
                min(255, int(v * 1.08)),
                min(255, int(v * 0.86)),
                min(255, int(v * 0.67)),
            )
    return sepia

# ── FILTROS ─────────────────────────────────────────────
FILTERS = {
    'grayscale': lambda im: ImageOps.grayscale(im.convert('RGB')).convert('RGB'),
    'sepia':     _apply_sepia,
    'blur':      lambda im: im.convert('RGB').filter(ImageFilter.GaussianBlur(radius=3)),
    'sharpen':   lambda im: im.convert('RGB').filter(ImageFilter.SHARPEN),
    'contour':   lambda im: im.convert('RGB').filter(ImageFilter.CONTOUR),
    'emboss':    lambda im: im.convert('RGB').filter(ImageFilter.EMBOSS),
    'flip_h':    lambda im: ImageOps.mirror(im.convert('RGB')),
    'flip_v':    lambda im: ImageOps.flip(im.convert('RGB')),
}

def apply_filter(file_name, new_name, filter_name):
    print(f"Aplicando filtro: {filter_name} → {new_name}", flush=True)
    im = Image.open(file_name)
    fn = FILTERS.get(filter_name.lower())
    if fn is None:
        raise ValueError(f"Filtro desconocido: '{filter_name}'. Opciones: {list(FILTERS)}")
    result = fn(im)
    # Asegurar RGB antes de guardar como jpg
    if result.mode != 'RGB':
        result = result.convert('RGB')
    result.save(new_name)
    print(f"Filtro guardado: {new_name} modo={result.mode}", flush=True)

# ── CONVERTIR FORMATO ────────────────────────────────────
def convert_image(file_name, new_name, fmt):
    print(f"Convirtiendo: {file_name} → {new_name} [{fmt}]", flush=True)
    im = Image.open(file_name)
    im = _normalize(im, fmt)
    im.save(new_name, format=fmt.upper())
    print(f"Conversión guardada: {new_name} modo={im.mode}", flush=True)