import fitz
from PIL import Image
from io import BytesIO
import base64

DPI_PRINTER = 203  # padrão Zebra
THRESHOLD = 180    # limiar binarização

def image_to_zpl_gfa(img):
    """Converte imagem 1-bit (modo '1') em bloco ^GFA (Zebra)"""
    if img.mode != '1':
        raise ValueError("A imagem deve estar em modo 1-bit ('1')")
    
    w, h = img.size
    bytes_per_row = (w + 7) // 8
    total_bytes = bytes_per_row * h

    pixels = img.load()
    hex_lines = []

    for y in range(h):
        row_bytes = bytearray(bytes_per_row)
        for x in range(w):
            byte_index = x // 8
            bit_index = 7 - (x % 8)
            bit = 1 if pixels[x, y] == 0 else 0  # preto=1
            if bit:
                row_bytes[byte_index] |= (1 << bit_index)
        hex_lines.append(row_bytes.hex().upper())

    hexdata = "".join(hex_lines)
    header = f"{total_bytes},{bytes_per_row},{bytes_per_row},"
    return header + hexdata

def pdf_to_zpl(pdf_bytes: bytes, dpi: int = DPI_PRINTER):
    """Converte cada página do PDF em código ZPL (^GFA)"""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    zpl_pages = []

    for i in range(len(doc)):
        page = doc.load_page(i)
        scale = dpi / 72
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)

        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img_gray = img.convert("L")
        img_bw = img_gray.point(lambda p: 0 if p < THRESHOLD else 255, "1")

        gfa = image_to_zpl_gfa(img_bw)
        zpl_block = f"^XA\n^LH0,0\n^FO0,0^GFA{gfa}^FS\n^XZ"
        zpl_pages.append(zpl_block)

    doc.close()
    return "\n\n".join(zpl_pages)
