import os,time,httpx
from contextlib import contextmanager
import psycopg
from fastapi import FastAPI,HTTPException
from pydantic import BaseModel
app=FastAPI(title="Enrollment Service")
URL=os.getenv("DATABASE_URL","postgresql://portaluser:portalpass@postgres:5432/studentportal")
US=os.getenv("USER_SERVICE_URL","http://user-service:8000");CS=os.getenv("COURSE_SERVICE_URL","http://course-service:8000")
class EnrollmentCreate(BaseModel):user_id:int;course_id:int
@contextmanager
def db():
    with psycopg.connect(URL) as c:yield c
def init():
    for _ in range(30):
        try:
            with db() as c:c.execute("CREATE TABLE IF NOT EXISTS enrollments(id SERIAL PRIMARY KEY,user_id INTEGER NOT NULL,course_id INTEGER NOT NULL,enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,UNIQUE(user_id,course_id))");c.commit();return
        except Exception:time.sleep(2)
    raise RuntimeError("database unavailable")
@app.on_event("startup")
def startup():init()
@app.get("/health")
def health():return {"service":"enrollment-service","status":"healthy"}
def get(url,label):
    try:r=httpx.get(url,timeout=5)
    except httpx.RequestError:raise HTTPException(503,f"{label} service unavailable")
    if r.status_code==404:raise HTTPException(400,f"{label} does not exist")
    if r.status_code>=400:raise HTTPException(503,f"{label} service error")
    return r.json()
@app.post("/enrollments",status_code=201)
def create(x:EnrollmentCreate):
    u=get(f"{US}/users/{x.user_id}","Student");co=get(f"{CS}/courses/{x.course_id}","Course")
    try:
        with db() as c:r=c.execute("INSERT INTO enrollments(user_id,course_id) VALUES(%s,%s) RETURNING id,user_id,course_id,enrolled_at",(x.user_id,x.course_id)).fetchone();c.commit()
    except psycopg.errors.UniqueViolation:raise HTTPException(409,"Student already enrolled")
    return {"id":r[0],"user_id":r[1],"student_name":u["name"],"course_id":r[2],"course_title":co["title"],"enrolled_at":r[3]}
@app.get("/enrollments")
def all():
    with db() as c:rows=c.execute("SELECT id,user_id,course_id,enrolled_at FROM enrollments ORDER BY id").fetchall()
    ans=[]
    for r in rows:
        u=get(f"{US}/users/{r[1]}","Student");co=get(f"{CS}/courses/{r[2]}","Course")
        ans.append({"id":r[0],"user_id":r[1],"student_name":u["name"],"course_id":r[2],"course_title":co["title"],"enrolled_at":r[3]})
    return ans
