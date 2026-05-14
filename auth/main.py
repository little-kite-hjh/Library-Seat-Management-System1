from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext

# ===================== 数据库（无需MySQL） =====================
SQLALCHEMY_DATABASE_URL = "sqlite:///./library.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ===================== 数据表 =====================
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True)
    password = Column(String(255))
    name = Column(String(20))
    role = Column(String(10), default="student")
    is_black = Column(Boolean, default=False)

class Seat(Base):
    __tablename__ = "seats"
    id = Column(Integer, primary_key=True)
    room = Column(String(20))
    number = Column(String(10))
    status = Column(String(10), default="available")

class Record(Base):
    __tablename__ = "records"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    seat_id = Column(Integer, ForeignKey("seats.id"))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    status = Column(String(15), default="reserved")
    create_time = Column(DateTime, default=datetime.now)

# ===================== 数据库依赖 =====================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ===================== 认证 =====================
SECRET_KEY = "test123"
ALGORITHM = "HS256"
# ===================== 修复 bcrypt 报错 + 密码超长问题 =====================
import hashlib
def hash_pwd(pwd: str) -> str:
    # 密码截断到 72 字节以内，避免 bcrypt 报错
    pwd = pwd.encode('utf-8')[:72].decode('utf-8', errors='ignore')
    return hashlib.sha256(pwd.encode()).hexdigest()

def verify_pwd(plain: str, hashed: str) -> bool:
    plain = plain.encode('utf-8')[:72].decode('utf-8', errors='ignore')
    return hash_pwd(plain) == hashed

def create_token(user_id, username, role):
    expire = datetime.utcnow() + timedelta(hours=2)
    return jwt.encode({"sub": username, "id": user_id, "role": role, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

# ===================== 数据格式 =====================
class UserCreate(BaseModel):
    username: str
    password: str
    name: str

class UserLogin(BaseModel):
    username: str
    password: str

# ===================== 主程序 =====================
app = FastAPI(
    title="校园图书馆座位预约系统",
    description="课程设计 - 人员B模块：用户、管理员、统计、预约管理",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

# ===================== 登录注册 =====================
@app.post("/register", summary="用户注册", tags=["用户模块"])
def register(data: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="学号已存在")
    user = User(username=data.username, password=hash_pwd(data.password), name=data.name)
    db.add(user)
    db.commit()
    return {"msg": "注册成功"}

@app.post("/login", summary="用户登录", tags=["用户模块"])
def login(data: UserLogin, db: Session = Depends(get_db)):
    # 1. 校验用户是否注册（核心：查询数据库）
    user = db.query(User).filter(User.username == data.username).first()
    if not user:
        # 未注册用户直接拒绝登录
        raise HTTPException(status_code=400, detail="该学号未注册，请先注册")
    
    # 2. 校验密码是否正确
    if not verify_pwd(data.password, user.password):
        raise HTTPException(status_code=400, detail="密码错误")
    
    # 3. 可选：黑名单用户禁止登录（增强逻辑）
    if user.is_black:
        raise HTTPException(status_code=403, detail="你已被加入黑名单，禁止登录")
    
    # 4. 生成token返回
    token = create_token(user.id, user.username, user.role)
    return {"token": token, "role": user.role}

# ===================== 当前用户 =====================
def get_current_user(token: str = Depends(lambda: None), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user = db.query(User).filter(User.username == payload["sub"]).first()
        return user
    except:
        raise HTTPException(status_code=401, detail="未登录")

# ===================== 管理员权限 =====================
def admin_required(user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="无管理员权限")
    return user

# ===================== 我的预约 =====================
@app.get("/my/records", summary="我的预约记录", tags=["预约模块"])
def my_records(user=Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Record).filter(Record.user_id == user.id).all()

# ===================== 取消预约 =====================
@app.post("/record/cancel/{rid}", summary="取消预约", tags=["预约模块"])
def cancel(rid: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    record = db.query(Record).filter(Record.id == rid, Record.user_id == user.id).first()
    if not record:
        raise HTTPException(status_code=404, detail="预约不存在")
    record.status = "canceled"
    seat = db.query(Seat).filter(Seat.id == record.seat_id).first()
    seat.status = "available"
    db.commit()
    return {"msg": "取消成功"}

# ===================== 管理员：所有预约 =====================
@app.get("/admin/records", summary="查看全部预约", tags=["管理员模块"])
def admin_all_records(db: Session = Depends(get_db), user=Depends(admin_required)):
    return db.query(Record).all()

# ===================== 管理员：座位维护 =====================
@app.post("/admin/seat/maintain/{sid}", summary="设置座位维护", tags=["管理员模块"])
def set_maintain(sid: int, db: Session = Depends(get_db), user=Depends(admin_required)):
    seat = db.query(Seat).filter(Seat.id == sid).first()
    seat.status = "maintain"
    db.commit()
    return {"msg": "已设置为维护状态"}

# ===================== 管理员：黑名单 =====================
@app.post("/admin/black/{uid}", summary="加入黑名单", tags=["管理员模块"])
def add_black(uid: int, db: Session = Depends(get_db), user=Depends(admin_required)):
    user = db.query(User).filter(User.id == uid).first()
    user.is_black = True
    db.commit()
    return {"msg": "已加入黑名单"}

# ===================== 统计：使用率 =====================
@app.get("/stats/usage", summary="座位使用率统计", tags=["统计模块"])
def usage(db: Session = Depends(get_db)):
    total = db.query(Seat).count()
    used = db.query(Seat).filter(Seat.status == "used").count()
    rate = round(used / total * 100, 2) if total else 0
    return {"总座位数": total, "已使用": used, "使用率": f"{rate}%"}

# ===================== 统计：热门座位 =====================
@app.get("/stats/hot", summary="热门座位排行", tags=["统计模块"])
def hot_seats(db: Session = Depends(get_db)):
    return db.query(Record.seat_id, func.count(Record.id).label("预约次数"))\
        .group_by(Record.seat_id).order_by(func.count(Record.id).desc()).limit(10).all()

# ===================== 自定义中文文档 =====================
from fastapi.openapi.docs import get_swagger_ui_html
app.docs_url = None

@app.get("/docs", summary="接口文档", include_in_schema=False)
async def docs():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title="校园图书馆座位预约系统 - 接口文档",
        swagger_ui_parameters={
            "docExpansion": "none",
            "defaultModelsExpandDepth": -1,
            "syntaxHighlight.theme": "monokai"
        },
        custom_css="""
            /* 页面美化 */
            body { background: #f5f7fa; }
            .swagger-ui .topbar { background: #2d7dd2; }
            .swagger-ui .opblock { border-radius: 8px; box-shadow:0 2px 5px #00000010; }
            .swagger-ui .opblock-summary-container { background:#fff; }
            .swagger-ui .btn.execute { background:#2d7dd2; border-color:#2d7dd2; }
        """
    )

# ===================== 启动 =====================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)