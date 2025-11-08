# main.py — FastAPI WebApp para gerar etiquetas
import shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from backend.label_generator import generate_combined_pdf
from backend.label_matcher import match_pdf_with_excel



app = FastAPI(title="Conversor de Etiquetas Shopee")

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
TEMPLATE_DIR = BASE_DIR.parent / "frontend"
OUTPUT_FILE = BASE_DIR / "etiquetas_final.pdf"

UPLOAD_DIR.mkdir(exist_ok=True)
TEMPLATE_DIR.mkdir(exist_ok=True)

templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

# Monta pasta estática (CSS/JS, se quiser adicionar depois)
# Tenta usar a pasta 'static' dentro de backend, se não existir, usa a do frontend
STATIC_DIR = BASE_DIR / "static"
if not STATIC_DIR.exists():
    # tenta usar a pasta static do frontend (um nível acima)
    possible_front_static = BASE_DIR.parent / "frontend" / "static"
    if possible_front_static.exists():
        STATIC_DIR = possible_front_static
    else:
        STATIC_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")



@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload")
async def upload_files(pdf: UploadFile, xlsx: UploadFile):
    """
    Recebe PDF e Excel, salva localmente, gera etiquetas_final.pdf e retorna para download.
    """
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
