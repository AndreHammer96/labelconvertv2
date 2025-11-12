# backend/auth.py
from fastapi import APIRouter, Form, Request, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from passlib.hash import bcrypt
from datetime import date
from sqlalchemy.orm import Session
from .database import get_db
from . import models, deps
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="frontend")


# ------------------------------
# REGISTRO
# ------------------------------
@router.post("/register")
async def register_user(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    plan: str = Form("Basic"),
    db: Session = Depends(get_db),
):
    existing = db.query(models.User).filter(models.User.email == email).first()
    if existing:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "E-mail já cadastrado. Faça login."},
            status_code=400,
        )

    hashed = bcrypt.hash(password[:72])

    from dateutil.relativedelta import relativedelta

    data_expira = None
    plano_final = plan if plan else "Basic"
    if plano_final.lower() != "basic":
        data_expira = date.today() + relativedelta(years=1)

    new_user = models.User(
        nome=name,
        email=email,
        senha=hashed,
        plano=plano_final,
        data_inicio=date.today(),
        data_expira=data_expira,
    )

    db.add(new_user)
    db.commit()
    return RedirectResponse("/login?success=1", status_code=303)


# ------------------------------
# LOGIN
# ------------------------------
@router.post("/login")
async def login_user(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.email == email).first()

    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Usuário não encontrado. Verifique o e-mail ou cadastre-se."},
            status_code=400,
        )

    if not bcrypt.verify(password, user.senha):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Senha incorreta. Tente novamente."},
            status_code=400,
        )

    token = deps.create_access_token(user.email)
    response = RedirectResponse("/dashboard", status_code=303)
    response.set_cookie("auth_token", token, httponly=True, samesite="lax")
    return response


# ------------------------------
# LOGOUT
# ------------------------------
@router.post("/logout")
async def logout_user():
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("auth_token")
    return response


# ------------------------------
# RECUPERAÇÃO DE SENHA (básico)
# ------------------------------
@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse("forgot_password.html", {"request": request})


@router.post("/forgot-password")
async def forgot_password(
    request: Request,
    email: str = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        return templates.TemplateResponse(
            "forgot_password.html",
            {"request": request, "error": "E-mail não encontrado."},
            status_code=400,
        )

    hashed = bcrypt.hash(new_password[:72])
    user.senha = hashed
    db.commit()

    return templates.TemplateResponse(
        "login.html",
        {"request": request, "success": "Senha redefinida com sucesso. Faça login."},
    )
