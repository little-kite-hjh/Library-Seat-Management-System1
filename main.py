from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import csv
import os

# ------------------------------ 数据库 ------------------------------
DATABASE_URL = "sqlite:///./library.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ------------------------------ 模型 ------------------------------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True)
    password = Column(String(255))
    name = Column(String(20))
    role = Column(String(10), default="user")
    black = Column(Boolean, default=False)

class Classroom(Base):
    __tablename__ = "classrooms"
    id = Column(Integer, primary_key=True)
    name = Column(String(30))
    location = Column(String(50))
    capacity = Column(Integer)
    device = Column(String(100))
    status = Column(String(10), default="normal")

class Reserve(Base):
    __tablename__ = "reserves"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    classroom_id = Column(Integer)
    date = Column(String(20))
    time_slot = Column(String(20))
    status = Column(String(20), default="pending")
    create_time = Column(DateTime, default=datetime.now)

class Setting(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True)
    max_per_day = Column(Integer, default=2)
    max_hours = Column(Integer, default=4)
    need_audit = Column(Boolean, default=True)

Base.metadata.create_all(bind=engine)

# ------------------------------ 依赖 ------------------------------
def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# ------------------------------ 安全 ------------------------------
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET = "MEMBER_D_VERY_COOL"
ALGORITHM = "HS256"

def token(data: dict):
    return jwt.encode({"exp": datetime.utcnow() + timedelta(days=1), **data}, SECRET, algorithm=ALGORITHM)

# ------------------------------ 启动 ------------------------------
app = FastAPI(title="高级图书馆教室预约系统")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ------------------------------ 用户 ------------------------------
class UserIn(BaseModel):
    username: str
    password: str
    name: str

@app.post("/register")
def register(d: UserIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == d.username).first():
        raise HTTPException(400, "学号已注册")
    u = User(username=d.username, password=pwd.hash(d.password), name=d.name)
    db.add(u)
    db.commit()
    return {"code": 200, "msg": "注册成功"}

@app.post("/login")
def login(d: UserIn, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.username == d.username).first()
    if not u or not pwd.verify(d.password, u.password):
        raise HTTPException(400, "账号或密码错误")
    if u.black:
        raise HTTPException(403, "你已被禁止预约")
    return {"token": token({"id": u.id, "role": u.role}), "role": u.role, "uid": u.id, "name": u.name}

# ------------------------------ 教室 ------------------------------
@app.get("/classrooms")
def classrooms(db: Session = Depends(get_db)):
    return db.query(Classroom).all()

@app.post("/admin/classroom")
def add_room(name: str, location: str, capacity: int, device: str, db: Session = Depends(get_db)):
    db.add(Classroom(name=name, location=location, capacity=capacity, device=device))
    db.commit()
    return {"msg": "添加成功"}

# ------------------------------ 预约 ------------------------------
@app.get("/reserve/my")
def my_reserve(uid: int, db: Session = Depends(get_db)):
    return db.query(Reserve).filter(Reserve.user_id == uid).all()

@app.post("/reserve")
def reserve(uid: int, cid: int, date: str, slot: str, db: Session = Depends(get_db)):
    exist = db.query(Reserve).filter(Reserve.classroom_id==cid, Reserve.date==date, Reserve.time_slot==slot, Reserve.status != "canceled").first()
    if exist: raise HTTPException(400, "该时段已被预约")
    setting = db.query(Setting).first()
    if not setting: setting = Setting(max_per_day=2, max_hours=4, need_audit=True); db.add(setting); db.commit()
    daily = db.query(Reserve).filter(Reserve.user_id==uid, Reserve.date==date, Reserve.status != "canceled").count()
    if daily >= setting.max_per_day: raise HTTPException(400, f"今日最多预约{setting.max_per_day}次")
    status = "pending" if setting.need_audit else "approved"
    db.add(Reserve(user_id=uid, classroom_id=cid, date=date, time_slot=slot, status=status))
    db.commit()
    return {"msg": "预约成功"}

@app.post("/reserve/cancel")
def cancel(id: int, db: Session = Depends(get_db)):
    r = db.query(Reserve).filter(Reserve.id == id).first()
    r.status = "canceled"
    db.commit()
    return {"msg": "已取消"}

# ------------------------------ 管理员 ------------------------------
@app.get("/admin/reserves")
def admin_reserves(db: Session = Depends(get_db)):
    return db.query(Reserve).all()

@app.post("/admin/audit")
def audit(id: int, status: str, db: Session = Depends(get_db)):
    r = db.query(Reserve).filter(Reserve.id == id).first()
    r.status = status
    db.commit()
    return {"msg": "审核成功"}

@app.post("/admin/black")
def black(uid: int, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == uid).first()
    u.black = not u.black
    db.commit()
    return {"msg": "操作成功"}

@app.get("/admin/export")
def export(db: Session = Depends(get_db)):
    rs = db.query(Reserve).all()
    with open("export.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["ID", "用户ID", "教室ID", "日期", "时段", "状态"])
        for r in rs: w.writerow([r.id, r.user_id, r.classroom_id, r.date, r.time_slot, r.status])
    return FileResponse("export.csv", media_type="text/csv", filename="预约记录.csv")

# ------------------------------ 运行 ------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)