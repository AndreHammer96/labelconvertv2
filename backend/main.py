# main.py — FastAPI WebApp para gerar etiquetas
import shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from .label_generator import generate_combined_pdf
from .label_matcher import match_pdf_with_excel

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
