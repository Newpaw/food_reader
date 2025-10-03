Jasně, Honzo. Níže máš jednoduché, ale solidní „MVP-ready“ rozvržení pro FastAPI backend + čistý HTML/JS frontend bez build toolů. JWT pošleme v `Authorization: Bearer <token>` (ne do cookies, ať je to prosté). Obrázky půjdou přes `multipart/form-data`, metadata jako JSON nebo běžná pole. Databáze SQLite (rychlý start), snadno vyměnitelná za Postgres.

# Doporučená architektura

* **Auth:** e-mail + heslo, JWT access token (15–60 min), refresh endpoint volitelně později.
* **Upload fotek:** `multipart/form-data` (`image`, `calories`, `meal_type`, `consumed_at`, `notes`). Soubor uložíš na disk `uploads/<user_id>/<uuid>.jpg` a do DB uložíš cestu + metadata.
* **Frontend:** čisté `index.html` + `app.js` s `fetch()`. Token držený v `localStorage`.
* **API vrstvy:** `routers/` (oddělené moduly), `schemas.py` (Pydantic), `models.py` (SQLAlchemy/SQLModel), `crud.py` (DB operace), `auth.py` (JWT, hash hesel), `deps.py` (Depends), `settings.py` (env), `database.py` (Session).
* **Statika:** FastAPI servíruje `/static` a `/uploads` (read-only).

# Co posílat v requestech

* **Autorizace:** `Authorization: Bearer <JWT>` u všech chráněných endpointů.
* **Registrace/Login:** `application/json` — `{ email, password, name }`.
* **Upload jídla:** `multipart/form-data` — pole:

  * `image` – binárně (input type="file")
  * `calories` – number (integer)
  * `meal_type` – string (`breakfast|lunch|dinner|snack`)
  * `consumed_at` – ISO datetime (např. `2025-10-03T19:30:00Z`)
  * `notes` – optional string
* **Listing & součty:** query parametry `from`, `to`, `limit`, `offset`. Server spočítá agregace (kalorie/den, týden, měsíc).

---

# Struktura projektu

```
calorie-tracker/
├─ backend/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ settings.py
│  │  ├─ database.py
│  │  ├─ models.py
│  │  ├─ schemas.py
│  │  ├─ auth.py
│  │  ├─ crud.py
│  │  ├─ deps.py
│  │  └─ routers/
│  │     ├─ auth_router.py
│  │     ├─ meals_router.py
│  │     └─ users_router.py
│  ├─ uploads/            # generated at runtime
│  └─ static/             # optional (icons, styles)
├─ frontend/
│  ├─ index.html
│  ├─ login.html
│  └─ app.js
└─ pyproject.toml / requirements.txt
```

---

# Backend: klíčové soubory (zkrácené, produkčně použitelné)

**`settings.py`**

```python
# All comments are in English as requested.
from pydantic import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./calories.db"
    JWT_SECRET: str = "CHANGE_ME"
    JWT_ALG: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    UPLOAD_DIR: str = "backend/uploads"

settings = Settings()
```

**`database.py`**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .settings import settings

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
```

**`models.py`**

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    meals = relationship("Meal", back_populates="user")

class Meal(Base):
    __tablename__ = "meals"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    image_path = Column(String, nullable=False)
    calories = Column(Integer, nullable=False)
    meal_type = Column(String, nullable=False)  # breakfast|lunch|dinner|snack
    consumed_at = Column(DateTime, nullable=False)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="meals")
```

**`schemas.py`**

```python
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List

class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: str
    class Config: orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class MealCreate(BaseModel):
    calories: int
    meal_type: str
    consumed_at: datetime
    notes: Optional[str] = None

class MealOut(BaseModel):
    id: int
    calories: int
    meal_type: str
    consumed_at: datetime
    notes: Optional[str]
    image_url: str
    class Config: orm_mode = True

class DailySummary(BaseModel):
    date: datetime
    total_calories: int
    meals: int

class SummaryOut(BaseModel):
    from_dt: datetime
    to_dt: datetime
    days: List[DailySummary]
```

**`auth.py`**

```python
import time
import bcrypt
import jwt
from fastapi import HTTPException, status
from .settings import settings

def hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode()

def verify_password(raw: str, hashed: str) -> bool:
    return bcrypt.checkpw(raw.encode(), hashed.encode())

def create_access_token(sub: str) -> str:
    now = int(time.time())
    payload = {
        "sub": sub,
        "iat": now,
        "exp": now + settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "type": "access"
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
```

**`deps.py`**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from .database import SessionLocal
from .auth import decode_token
from . import models

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    payload = decode_token(token)
    user = db.query(models.User).filter(models.User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
```

**`crud.py`**

```python
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
```

**`routers/auth_router.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .. import schemas, crud
from ..deps import get_db
from ..auth import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=schemas.UserOut)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(crud.models.User).filter(crud.models.User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = crud.create_user(db, payload.email, payload.name, payload.password)
    return user

@router.post("/login", response_model=schemas.Token)
def login(form_data: schemas.UserCreate, db: Session = Depends(get_db)):
    user = crud.authenticate_user(db, form_data.email, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(str(user.id))
    return {"access_token": token, "token_type": "bearer"}
```

**`routers/meals_router.py`**

```python
import os, uuid
from datetime import datetime, date
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from ..deps import get_db, get_current_user
from ..settings import settings
from .. import models, schemas

router = APIRouter(prefix="/me", tags=["meals"])

@router.post("/meals", response_model=schemas.MealOut)
async def create_meal(
    calories: int = Form(...),
    meal_type: str = Form(...),
    consumed_at: datetime = Form(...),
    notes: str | None = Form(None),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    # Save file
    user_dir = os.path.join(settings.UPLOAD_DIR, str(user.id))
    os.makedirs(user_dir, exist_ok=True)
    ext = os.path.splitext(image.filename or "")[1].lower() or ".jpg"
    fname = f"{uuid.uuid4()}{ext}"
    path = os.path.join(user_dir, fname)

    with open(path, "wb") as f:
        f.write(await image.read())

    meal = models.Meal(
        user_id=user.id, image_path=path, calories=calories,
        meal_type=meal_type, consumed_at=consumed_at, notes=notes
    )
    db.add(meal); db.commit(); db.refresh(meal)

    return schemas.MealOut(
        id=meal.id,
        calories=meal.calories,
        meal_type=meal.meal_type,
        consumed_at=meal.consumed_at,
        notes=meal.notes,
        image_url=f"/uploads/{user.id}/{fname}"
    )

@router.get("/meals", response_model=List[schemas.MealOut])
def list_meals(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
    frm: str | None = None,
    to: str | None = None,
    limit: int = 50,
    offset: int = 0
):
    q = db.query(models.Meal).filter(models.Meal.user_id == user.id)
    if frm: q = q.filter(models.Meal.consumed_at >= frm)
    if to:  q = q.filter(models.Meal.consumed_at < to)
    q = q.order_by(models.Meal.consumed_at.desc()).offset(offset).limit(limit)
    meals = q.all()
    return [
        schemas.MealOut(
            id=m.id, calories=m.calories, meal_type=m.meal_type,
            consumed_at=m.consumed_at, notes=m.notes,
            image_url=f"/uploads/{user.id}/{os.path.basename(m.image_path)}"
        ) for m in meals
    ]

@router.get("/summary", response_model=schemas.SummaryOut)
def summary(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
    frm: str,
    to: str
):
    from_dt = datetime.fromisoformat(frm)
    to_dt = datetime.fromisoformat(to)
    rows = db.execute(
        """
        SELECT date(consumed_at) as d, SUM(calories) as total, COUNT(*) as meals
        FROM meals
        WHERE user_id = :uid AND consumed_at >= :f AND consumed_at < :t
        GROUP BY date(consumed_at)
        ORDER BY d
        """, {"uid": user.id, "f": from_dt, "t": to_dt}
    ).fetchall()

    days = [schemas.DailySummary(date=datetime.fromisoformat(r[0]+"T00:00:00"), total_calories=r[1], meals=r[2]) for r in rows]
    return schemas.SummaryOut(from_dt=from_dt, to_dt=to_dt, days=days)
```

**`routers/users_router.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..deps import get_db, get_current_user
from .. import schemas, models

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(get_current_user)):
    return user
```

**`main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .database import Base, engine
from .settings import settings
from .routers import auth_router, meals_router, users_router
import os

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Calorie Tracker")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"]
)

# Static serving for uploaded images
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Routers
app.include_router(auth_router.router)
app.include_router(users_router.router)
app.include_router(meals_router.router)
```

**`requirements.txt`**

```
fastapi
uvicorn[standard]
pydantic
sqlalchemy
bcrypt
PyJWT
python-multipart
```

---

# Frontend: minimalistický bez kompilace

**`login.html`**

```html
<!doctype html>
<html>
  <body>
    <h1>Login</h1>
    <input id="email" placeholder="Email" />
    <input id="password" type="password" placeholder="Password" />
    <button id="loginBtn">Sign in</button>
    <script>
      async function login() {
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const res = await fetch('/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password, name: 'n/a' })
        });
        if (!res.ok) return alert('Login failed');
        const data = await res.json();
        localStorage.setItem('token', data.access_token);
        location.href = '/frontend/index.html';
      }
      document.getElementById('loginBtn').onclick = login;
    </script>
  </body>
</html>
```

**`index.html`**

```html
<!doctype html>
<html>
  <body>
    <h1>Calorie Tracker</h1>
    <form id="mealForm">
      <input type="number" name="calories" placeholder="Calories" required />
      <select name="meal_type">
        <option>breakfast</option><option>lunch</option><option>dinner</option><option>snack</option>
      </select>
      <input type="datetime-local" name="consumed_at" required />
      <input type="text" name="notes" placeholder="Notes" />
      <input type="file" name="image" accept="image/*" required />
      <button type="submit">Upload</button>
    </form>
    <div id="list"></div>
    <script src="app.js"></script>
  </body>
</html>
```

**`app.js`**

```javascript
function authHeaders() {
  const t = localStorage.getItem('token');
  return t ? { Authorization: `Bearer ${t}` } : {};
}

document.getElementById('mealForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = e.target;
  const fd = new FormData(form);
  // Convert local datetime to ISO
  const dt = new Date(fd.get('consumed_at'));
  fd.set('consumed_at', dt.toISOString());

  const res = await fetch('/me/meals', {
    method: 'POST',
    headers: authHeaders(),
    body: fd
  });
  if (!res.ok) return alert('Upload failed');
  form.reset();
  loadMeals();
});

async function loadMeals() {
  const res = await fetch('/me/meals?limit=20', { headers: authHeaders() });
  if (!res.ok) return alert('Auth required');
  const items = await res.json();
  const list = document.getElementById('list');
  list.innerHTML = items.map(m => `
    <div style="margin:8px 0;padding:8px;border:1px solid #ddd;">
      <img src="${m.image_url}" style="max-width:200px;display:block;margin-bottom:6px"/>
      <div><b>${m.meal_type}</b> — ${m.calories} kcal</div>
      <div>${new Date(m.consumed_at).toLocaleString()}</div>
      <div>${m.notes ?? ''}</div>
    </div>
  `).join('');
}

loadMeals();
```

> Poznámka: frontend nasměruj tak, aby se servíroval z Nginx nebo přímo ze složky `/frontend` (např. reverzní proxy před FastAPI). Pro rychlý start můžeš otevřít `login.html` z disku a změnit URL fetchů na `http://localhost:8000/...`.

---

# Rychlé spuštění

```bash
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```

---

# Další tipy bez kudrlinek

* **Bezpečnost:** až půjdeš na produkci, přidej limit velikosti uploadu, validaci MIME, antivir scanning dle potřeby, a presignované URL pokud přesuneš fotky do S3/Blob.
* **Výkon:** malé obrázky klidně komprimuj (Pillow) a vytvářej náhledy.
* **Refresh tokeny:** přidej `/auth/refresh` s dlouhodobým refresh tokenem v httpOnly cookie, pokud nechceš spoléhat na časté přihlášení.
* **Metriky:** agregace v SQL, případně materializovaný pohled/tabulka pro denní součty.
* **Migrace:** až přerosteš SQLite, přidej Alembic a přepni na Postgres.

Chceš to zabalit do jednoho repa s minimal demo daty a pár `curl` příklady? Můžu ti to rovnou připravit.
