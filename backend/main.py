# main.py — FastAPI WebApp para gerar etiquetas
import shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from .label_generator import generate_combined_pdf
from .label_matcher import match_pdf_with_excel
from pdf2image import convert_from_bytes
from PIL import Image
import base64
from io import BytesIO
import tempfile
import os
import zipfile

app = FastAPI(title="Conversor de Etiquetas Shopee")

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"

# Detecta automaticamente o caminho correto do frontend
possible_paths = [
    BASE_DIR / "frontend",
    BASE_DIR.parent / "frontend",
    Path("/app/frontend"),  # caminho usado no Railway
]
for p in possible_paths:
    if (p / "index.html").exists():
        TEMPLATE_DIR = p
        break
else:
    TEMPLATE_DIR = BASE_DIR  # fallback

print(f"🧭 Usando TEMPLATE_DIR = {TEMPLATE_DIR}")

OUTPUT_FILE = BASE_DIR / "etiquetas_final.pdf"

UPLOAD_DIR.mkdir(exist_ok=True)
TEMPLATE_DIR.mkdir(exist_ok=True)

templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

# Monta pasta estática (CSS/JS)
STATIC_DIR = BASE_DIR / "static"
if not STATIC_DIR.exists():
    possible_front_static = BASE_DIR.parent / "frontend" / "static"
    if possible_front_static.exists():
        STATIC_DIR = possible_front_static
    else:
        STATIC_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# =====================
# Rotas principais
# =====================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/teste", response_class=HTMLResponse)
async def test_page(request: Request):
    return templates.TemplateResponse("teste.html", {"request": request})


@app.post("/upload")
async def upload_files(pdf: UploadFile, xlsx: UploadFile):
    """Recebe PDF e Excel, salva localmente, gera etiquetas_final.pdf e retorna para download."""
    pdf_path = UPLOAD_DIR / pdf.filename
    xlsx_path = UPLOAD_DIR / xlsx.filename

    # salva os uploads
    with pdf_path.open("wb") as f:
        shutil.copyfileobj(pdf.file, f)
    with xlsx_path.open("wb") as f:
        shutil.copyfileobj(xlsx.file, f)

    print(f"📥 PDF recebido: {pdf_path.name}")
    print(f"📥 XLSX recebido: {xlsx_path.name}")

    # gera PDF final
    generate_combined_pdf(pdf_path, xlsx_path, OUTPUT_FILE)

    return FileResponse(
        OUTPUT_FILE,
        media_type="application/pdf",
        filename="etiquetas_final.pdf",
    )


# =====================
# Rota genérica para páginas HTML adicionais
# =====================
@app.get("/{page_name}", response_class=HTMLResponse)
async def serve_page(request: Request, page_name: str):
    """
    Permite abrir qualquer página HTML da pasta frontend, como /planos.html
    """
    page_path = TEMPLATE_DIR / page_name
    if page_path.exists() and page_path.suffix == ".html":
        return templates.TemplateResponse(page_name, {"request": request})
    raise HTTPException(status_code=404, detail="Página não encontrada")


def image_to_zpl(image: Image.Image) -> str:
    """
    Converte PIL Image para ZPL GFA. Observação: a função atualmente inverte
    cores (branco->preto, preto->branco) usando Image.eval(...).
    Se preferir manter as cores originais, remova a linha de inversão.
    """
    # converter para 1-bit
    image = image.convert("1")
    # inverte cores para ZPL (se estiver invertendo no seu caso, remova a linha abaixo)
    image = Image.eval(image, lambda x: 255 - x)
    width, height = image.size
    bytes_per_row = (width + 7) // 8
    total_bytes = bytes_per_row * height
    data = bytearray(image.tobytes())
    hex_data = ''.join(f'{b:02X}' for b in data)
    return f"^XA\n^FO0,0^GFA,{total_bytes},{total_bytes},{bytes_per_row},{hex_data}^XZ"


@app.post("/generate_zpl_image/")
async def generate_zpl_image(file: UploadFile):
    """
    Retorna todos os ZPLs em lista (para preview e download).
    """
    content = await file.read()
    images = convert_from_bytes(content, dpi=203)
    zpl_list = [image_to_zpl(img) for img in images]
    return JSONResponse({"zpl": zpl_list})


@app.post("/preview_zpl/")
async def preview_zpl(file: UploadFile):
    """
    Gera um preview PNG apenas da primeira etiqueta (reduzido).
    """
    content = await file.read()
    # Converte o PDF para imagem em 100 DPI (mais leve)
    images = convert_from_bytes(content, dpi=100)
    if not images:
        raise HTTPException(status_code=400, detail="PDF sem páginas")

    first_image = images[0]

    # Converte a imagem para PNG em memória
    img_byte_arr = BytesIO()
    first_image.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)

    # Retorna o preview diretamente como imagem
    return StreamingResponse(img_byte_arr, media_type="image/png")


@app.post("/generate_zpl_full/")
async def generate_zpl_full(file: UploadFile):
    """
    Retorna um .zip com todos os .zpl das etiquetas convertidas.
    """
    content = await file.read()
    images = convert_from_bytes(content, dpi=203)
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "etiquetas_zpl.zip")

    with zipfile.ZipFile(zip_path, "w") as zf:
        for i, img in enumerate(images):
            zpl_code = image_to_zpl(img)
            zf.writestr(f"etiqueta_{i+1:03}.zpl", zpl_code)
    return FileResponse(zip_path, filename="etiquetas_zpl.zip")


@app.post("/generate_zpl_concat/")
async def generate_zpl_concat(file: UploadFile):
    """
    Retorna um único arquivo .zpl com todas as etiquetas concatenadas.
    """
    content = await file.read()
    images = convert_from_bytes(content, dpi=203)
    zpl_all = "\n".join(image_to_zpl(img) for img in images)
    temp_dir = tempfile.mkdtemp()
    path = os.path.join(temp_dir, "etiquetas_todas.zpl")
    with open(path, "w", encoding="utf-8") as f:
        f.write(zpl_all)
    return FileResponse(path, filename="etiquetas_todas.zpl")
