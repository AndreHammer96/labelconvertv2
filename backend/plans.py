# backend/plans.py
from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from dateutil.relativedelta import relativedelta
from .database import get_db
from . import models, deps

router = APIRouter()


@router.get("/me")
async def me(request: Request, db: Session = Depends(get_db)):
    user = deps.get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não autenticado")
    return {
        "nome": user.nome,
        "email": user.email,
        "plano": user.plano,
        "data_expira": str(user.data_expira),
    }


@router.post("/assinatura/{plano_id}")
async def criar_assinatura(plano_id: int, request: Request, db: Session = Depends(get_db)):
    user = deps.get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não autenticado")

    plano = db.query(models.Plano).filter(models.Plano.id == plano_id).first()
    if not plano:
        raise HTTPException(status_code=404, detail="Plano não encontrado")

    # Mock (depois integre com Gerencianet)
    txid = f"TXID-{user.id}-{plano_id}"
    assinatura = models.Assinatura(
        user_id=user.id,
        plano_id=plano.id,
        status="pendente",
        txid=txid,
    )
    db.add(assinatura)
    db.commit()
    return {"txid": txid, "valor": plano.preco, "mensagem": "Assinatura criada (mock PIX)"}
