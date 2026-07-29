import os,time
from contextlib import contextmanager
import psycopg
from fastapi import FastAPI,HTTPException
from pydantic import BaseModel
app=FastAPI(title="Course Service")
URL=os.getenv("DATABASE_URL","postgresql://portaluser:portalpass@postgres:5432/studentportal")
class CourseCreate(BaseModel): title:str; description:str
@contextmanager
def db():
    with psycopg.connect(URL) as c: yield c
def init():
    for _ in range(30):
        try:
            with db() as c:c.execute("CREATE TABLE IF NOT EXISTS courses(id SERIAL PRIMARY KEY,title VARCHAR(160) NOT NULL,description TEXT NOT NULL,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)");c.commit();return
        except Exception:time.sleep(2)
    raise RuntimeError("database unavailable")
@app.on_event("startup")
def startup():init()
@app.get("/health")
def health():return {"service":"course-service","status":"healthy"}
@app.post("/courses",status_code=201)
def create(x:CourseCreate):
    with db() as c:r=c.execute("INSERT INTO courses(title,description) VALUES(%s,%s) RETURNING id,title,description,created_at",(x.title,x.description)).fetchone();c.commit()
    return dict(zip(["id","title","description","created_at"],r))
@app.get("/courses")
def all():
    with db() as c:r=c.execute("SELECT id,title,description,created_at FROM courses ORDER BY id").fetchall()
    return [dict(zip(["id","title","description","created_at"],x)) for x in r]
@app.get("/courses/{id}")
def one(id:int):
    with db() as c:r=c.execute("SELECT id,title,description,created_at FROM courses WHERE id=%s",(id,)).fetchone()
    if not r:raise HTTPException(404,"Course not found")
    return dict(zip(["id","title","description","created_at"],r))
