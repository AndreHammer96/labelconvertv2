# backend/deps.py
from fastapi import Request
from jose import jwt, JWTError
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from .database import get_db
from . import models

SECRET_KEY = "troque-por-uma-chave-muito-secreta"
ALGORITHM = "HS256"


def create_access_token(subject: str, hours_valid=12):
    expire = datetime.utcnow() + timedelta(hours=hours_valid)
    to_encode = {"sub": subject, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user_email(request: Request):
    token = request.cookies.get("auth_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


def get_current_user(request: Request, db: Session):
    email = get_current_user_email(request)
    if not email:
        return None
    return db.query(models.User).filter(models.User.email == email).first()
