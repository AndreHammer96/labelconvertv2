# backend/cron_jobs.py
from datetime import date
from .database import SessionLocal
from .models import User


def expire_plans():
    db = SessionLocal()
    today = date.today()
    users = db.query(User).filter(User.data_expira != None).all()
    for user in users:
        if user.data_expira and user.data_expira < today:
            user.plano = "free"
            user.data_expira = None
    db.commit()
    db.close()


if __name__ == "__main__":
    expire_plans()
