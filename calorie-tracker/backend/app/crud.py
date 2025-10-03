from sqlalchemy.orm import Session
from . import models
from .auth import hash_password, verify_password

def create_user(db: Session, email: str, name: str, password: str) -> models.User:
    user = models.User(email=email, name=name, password_hash=hash_password(password))
    db.add(user); db.commit(); db.refresh(user)
    return user

def authenticate_user(db: Session, email: str, password: str) -> models.User | None:
    user = db.query(models.User).filter(models.User.email == email).first()
    if user and verify_password(password, user.password_hash):
        return user
    return None