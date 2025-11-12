# backend/models.py
from sqlalchemy import Column, Integer, String, Date, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import date
from .database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String)
    email = Column(String, unique=True, index=True)
    senha = Column(String)
    plano = Column(String, default="free")
    data_inicio = Column(Date, nullable=True)
    data_expira = Column(Date, nullable=True)
    ativo = Column(Boolean, default=True)


class Plano(Base):
    __tablename__ = "planos"
    id = Column(Integer, primary_key=True)
    nome = Column(String)
    preco = Column(Float)
    duracao_meses = Column(Integer)
    descricao = Column(String)


class Assinatura(Base):
    __tablename__ = "assinaturas"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    plano_id = Column(Integer, ForeignKey("planos.id"))
    data_inicio = Column(Date)
    data_expira = Column(Date)
    status = Column(String, default="pendente")
    txid = Column(String)
    user = relationship("User")
    plano = relationship("Plano")
