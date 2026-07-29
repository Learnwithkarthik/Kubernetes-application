import os,time
from contextlib import contextmanager
import psycopg
from fastapi import FastAPI,HTTPException
from pydantic import BaseModel,EmailStr
app=FastAPI(title="User Service")
URL=os.getenv("DATABASE_URL","postgresql://portaluser:portalpass@postgres:5432/studentportal")
class UserCreate(BaseModel): name:str; email:EmailStr
@contextmanager
def db():
    with psycopg.connect(URL) as c: yield c
def init():
    for _ in range(30):
        try:
            with db() as c:
                c.execute("CREATE TABLE IF NOT EXISTS users(id SERIAL PRIMARY KEY,name VARCHAR(120) NOT NULL,email VARCHAR(200) UNIQUE NOT NULL,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)");c.commit();return
        except Exception: time.sleep(2)
    raise RuntimeError("database unavailable")
@app.on_event("startup")
def startup(): init()
@app.get("/health")
def health(): return {"service":"user-service","status":"healthy"}
@app.post("/users",status_code=201)
def create(x:UserCreate):
    try:
        with db() as c:
            r=c.execute("INSERT INTO users(name,email) VALUES(%s,%s) RETURNING id,name,email,created_at",(x.name,x.email)).fetchone();c.commit()
        return dict(zip(["id","name","email","created_at"],r))
    except psycopg.errors.UniqueViolation: raise HTTPException(409,"Email already exists")
@app.get("/users")
def all():
    with db() as c:r=c.execute("SELECT id,name,email,created_at FROM users ORDER BY id").fetchall()
    return [dict(zip(["id","name","email","created_at"],x)) for x in r]
@app.get("/users/{id}")
def one(id:int):
    with db() as c:r=c.execute("SELECT id,name,email,created_at FROM users WHERE id=%s",(id,)).fetchone()
    if not r: raise HTTPException(404,"Student not found")
    return dict(zip(["id","name","email","created_at"],r))
