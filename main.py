import os
import sqlite3
import datetime
import hashlib
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, status, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import jwt
import httpx

# Database setup
DB_NAME = "expenses.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Security Config
SECRET_KEY = "expense-tracker-secret-key-change-in-production"
ALGORITHM = "HS256"

# OAuth Credentials (ใช้ค่าจำลองเพื่อไม่ให้ GitHub บล็อก)
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "Ov23li6bWeCK86pKyVNi")
GITHUB_CLIENT_SECRET = os.getenv(
    "GITHUB_CLIENT_SECRET", "YOUR_GITHUB_CLIENT_SECRET"
)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "YOUR_GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv(
    "GOOGLE_CLIENT_SECRET", "YOUR_GOOGLE_CLIENT_SECRET"
)

app = FastAPI(
    title="Daily Expense Tracker API",
    description="ระบบบันทึกและจัดการรายจ่ายประจำวัน พร้อม Authentication & Validation",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper Functions
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(days=7)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user_from_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Token ไม่ถูกต้อง")
        return username
    except Exception:
        raise HTTPException(status_code=401, detail="Token หมดอายุหรือไม่ถูกต้อง")

# Pydantic Validation Schemas
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[str] = None
    password: str = Field(..., min_length=4)

class UserLogin(BaseModel):
    username: str
    password: str

class ExpenseCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    amount: float = Field(..., gt=0, description="จำนวนเงินต้องมากกว่า 0")
    category: str = Field(..., min_length=1)
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="รูปแบบ YYYY-MM-DD")
    note: Optional[str] = ""

class ExpenseUpdate(BaseModel):
    title: Optional[str] = None
    amount: Optional[float] = Field(None, gt=0)
    category: Optional[str] = None
    date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    note: Optional[str] = None

# Routes
@app.get("/")
def read_root():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return HTMLResponse("<h1>index.html not found</h1>")

@app.get("/favicon.ico")
def get_favicon():
    return JSONResponse(status_code=204, content={})

# 1. Authentication Endpoints
@app.post("/api/register")
def register(user: UserCreate):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (user.username,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="ชื่อผู้ใช้นี้ถูกใช้งานแล้ว")
    
    hashed_pwd = hash_password(user.password)
    cursor.execute(
        "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
        (user.username, user.email, hashed_pwd)
    )
    conn.commit()
    conn.close()
    return {"message": "สมัครสมาชิกสำเร็จเรียบร้อย"}

@app.post("/api/login")
def login(user: UserLogin):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (user.username,))
    db_user = cursor.fetchone()
    conn.close()

    if not db_user or not verify_password(user.password, db_user["password_hash"]):
        raise HTTPException(status_code=400, detail="ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
    
    token = create_access_token(data={"sub": db_user["username"]})
    return {"access_token": token, "token_type": "bearer", "username": db_user["username"]}

# GitHub OAuth
@app.get("/auth/github")
def github_login():
    github_url = f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&scope=user:email"
    return RedirectResponse(github_url)

@app.get("/auth/github/callback")
async def github_callback(code: str):
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
            }
        )
        token_json = token_res.json()
        access_token = token_json.get("access_token")

        if not access_token:
            raise HTTPException(status_code=400, detail="ไม่สามารถดึง Access Token จาก GitHub ได้")

        user_res = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "User-Agent": "ExpenseTrackerApp"
            }
        )
        user_data = user_res.json()
        username = user_data.get("login")

        if not username:
            raise HTTPException(status_code=400, detail="ไม่สามารถดึงชื่อผู้ใช้จาก GitHub ได้")

        avatar_url = user_data.get("avatar_url", "")
        github_profile_url = user_data.get("html_url", f"https://github.com/{username}")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username, f"{username}@github.oauth", hash_password("oauth_pass"))
            )
            conn.commit()
        conn.close()

        jwt_token = create_access_token(data={"sub": username})
        return RedirectResponse(
            url=f"/?token={jwt_token}&username={username}&avatar={avatar_url}&github={github_profile_url}"
        )

# Google OAuth
@app.get("/auth/google")
def google_login():
    google_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}&"
        f"response_type=code&"
        f"scope=openid%20email%20profile&"
        f"redirect_uri=http://localhost:8000/auth/google/callback"
    )
    return RedirectResponse(google_url)

@app.get("/auth/google/callback")
async def google_callback(code: str):
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": "http://localhost:8000/auth/google/callback",
            }
        )
        token_json = token_res.json()
        access_token = token_json.get("access_token")

        if not access_token:
            raise HTTPException(status_code=400, detail="ไม่สามารถดึง Access Token จาก Google ได้")

        user_res = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        user_data = user_res.json()
        email = user_data.get("email", "")
        username = email.split("@")[0] if email else "google_user"
        avatar_url = user_data.get("picture", "")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, hash_password("oauth_pass"))
            )
            conn.commit()
        conn.close()

        jwt_token = create_access_token(data={"sub": username})
        return RedirectResponse(
            url=f"/?token={jwt_token}&username={username}&avatar={avatar_url}"
        )

# 2. Expense CRUD API Endpoints (พร้อมตัวกรอง search, category, start_date, end_date)
@app.get("/api/expenses")
def get_expenses(
    token: str,
    search: Optional[str] = None,
    category: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    username = get_current_user_from_token(token)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="ไม่พบผู้ใช้")
    
    query = "SELECT * FROM expenses WHERE user_id = ?"
    params = [user["id"]]

    if search:
        query += " AND (title LIKE ? OR note LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    if category and category != "ทั้งหมด":
        query += " AND category = ?"
        params.append(category)
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)

    query += " ORDER BY date DESC, id DESC"
    cursor.execute(query, params)
    expenses = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return expenses

@app.post("/api/expenses")
def create_expense(expense: ExpenseCreate, token: str):
    username = get_current_user_from_token(token)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    
    cursor.execute(
        "INSERT INTO expenses (user_id, title, amount, category, date, note) VALUES (?, ?, ?, ?, ?, ?)",
        (user["id"], expense.title, expense.amount, expense.category, expense.date, expense.note)
    )
    conn.commit()
    conn.close()
    return {"message": "บันทึกรายการรายจ่ายสำเร็จ"}

@app.put("/api/expenses/{expense_id}")
def update_expense(expense_id: int, expense: ExpenseUpdate, token: str):
    username = get_current_user_from_token(token)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()

    cursor.execute("SELECT * FROM expenses WHERE id = ? AND user_id = ?", (expense_id, user["id"]))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="ไม่พบรายการรายจ่ายนี้")

    title = expense.title if expense.title is not None else existing["title"]
    amount = expense.amount if expense.amount is not None else existing["amount"]
    category = expense.category if expense.category is not None else existing["category"]
    date = expense.date if expense.date is not None else existing["date"]
    note = expense.note if expense.note is not None else existing["note"]

    cursor.execute(
        "UPDATE expenses SET title=?, amount=?, category=?, date=?, note=? WHERE id=?",
        (title, amount, category, date, note, expense_id)
    )
    conn.commit()
    conn.close()
    return {"message": "แก้ไขรายการรายจ่ายสำเร็จ"}

@app.delete("/api/expenses/{expense_id}")
def delete_expense(expense_id: int, token: str):
    username = get_current_user_from_token(token)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()

    cursor.execute("DELETE FROM expenses WHERE id = ? AND user_id = ?", (expense_id, user["id"]))
    conn.commit()
    conn.close()
    return {"message": "ลบรายการรายจ่ายสำเร็จ"}