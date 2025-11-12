# backend/auth.py
from fastapi import APIRouter, Form, Request, Depends
from fastapi.responses import RedirectResponse
from passlib.hash import bcrypt
from datetime import date
from sqlalchemy.orm import Session
from .database import get_db
from . import models, deps

router = APIRouter()


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
        return RedirectResponse("/register?error=email_exists", status_code=303)

    hashed = bcrypt.hash(password[:72])

    from datetime import timedelta

    # Define data de expiração para planos pagos
    data_expira = None
    plano_final = plan if plan else "Basic"

    if plano_final.lower() != "basic":
        data_expira = date.today() + timedelta(days=365)

    new_user = models.User(
        nome=name,
        email=email,
        senha=hashed,
        plano=plano_final,
        data_inicio=date.today(),
        data_expira=data_expira
    )

    db.add(new_user)
    db.commit()
    return RedirectResponse("/login", status_code=303)



@router.post("/login")
async def login_user(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not bcrypt.verify(password, user.senha):
        return RedirectResponse("/login?error=invalid", status_code=303)

    token = deps.create_access_token(user.email)
    response = RedirectResponse("/dashboard", status_code=303)
    response.set_cookie("auth_token", token, httponly=True, samesite="lax")
    return response


@router.post("/logout")
async def logout_user():
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("auth_token")
    return response
